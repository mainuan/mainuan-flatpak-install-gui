"""Bounded, immutable input snapshots. No network or shell execution here."""
import base64
import configparser
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import stat
from urllib.parse import urlsplit
from i18n import _

LIMIT = 1024 * 1024


def https_url(value):
    try:
        parsed = urlsplit(value)
        valid = (parsed.scheme == 'https' and parsed.hostname and not parsed.username
                 and not parsed.password and not parsed.fragment and parsed.port != 0)
    except ValueError:
        valid = False
    if not valid or any(c.isspace() or ord(c) < 32 or c == '\\' for c in value):
        raise ValueError(_('The source must use HTTPS without credentials or fragments in the URL.'))
    return value


def section_from_bytes(raw, group):
    if len(raw) > LIMIT or b'\x00' in raw:
        raise ValueError(_('Reference too large or with null bytes.'))
    parser = configparser.ConfigParser(interpolation=None, strict=True, delimiters=('=',),
                                       comment_prefixes=('#',), empty_lines_in_values=False)
    parser.optionxform = str
    try:
        parser.read_string(raw.decode('utf-8-sig'))
        if parser.defaults() or parser.sections() != [group]:
            raise ValueError(_('Invalid reference group.'))
        data = dict(parser[group])
        if any('\n' in v or '\r' in v for v in data.values()):
            raise ValueError(_('Multi-line fields are not accepted.'))
        return data
    except (UnicodeError, configparser.Error, KeyError) as exc:
        raise ValueError(_('Invalid Flatpak reference.')) from exc


def gpg_key(value):
    try:
        return base64.b64decode(value, validate=True) if value else b''
    except ValueError as exc:
        raise ValueError(_('Invalid GPG key.')) from exc


@dataclass(frozen=True)
class RemoteSpec:
    url: str
    suggested: str
    title: str
    key: bytes | None = b''
    collection: str = ''
    descriptor: str = ''
    default_branch: str = ''

    def notice(self):
        fingerprint = (_('not provided by the libflatpak proposal signal') if self.key is None
                       else hashlib.sha256(self.key).hexdigest() if self.key
                       else _('absent — GPG signature disabled'))
        return (_('Source: {url}\nSuggested name: {name}\n'
                  'Descriptor: {descriptor}\nSHA-256 of the provided key: {fingerprint}\n'
                  'HTTPS protects the transport; it does not guarantee that this source is trustworthy. '
                  'Adding the source changes the Flatpak configuration now. '
                  'It may remain even if the installation is cancelled.').format(
                    url=self.url, name=self.suggested, descriptor=self.descriptor or _('local file'),
                    fingerprint=fingerprint))


def friendly_name(app_id, title='', appstream=''):
    """Presentation only. A final ID component is a fallback, not a brand rule."""
    technical = re.compile(re.escape(app_id) + r' from [A-Za-z0-9][A-Za-z0-9._-]*')
    for candidate in (appstream, title):
        candidate = candidate.strip() if isinstance(candidate, str) else ''
        if candidate and candidate != app_id and not technical.fullmatch(candidate):
            return candidate
    return app_id.rsplit('.', 1)[-1]


@dataclass(frozen=True)
class Reference:
    raw: bytes
    app_id: str
    title: str
    branch: str
    remote: RemoteSpec
    runtime_repo: str = ''
    icon_name: str = ''

    @property
    def display_name(self):
        return friendly_name(self.app_id, self.title)

    @property
    def info(self):
        return {'name': self.display_name, 'description': '', 'id': self.app_id, 'source': self.remote.url,
                'runtimeRepo': self.runtime_repo}


def parse_reference(raw):
    s = section_from_bytes(raw, 'Flatpak Ref')
    if s.get('Version', '1') != '1':
        raise ValueError(_('Reference version not supported yet.'))
    supported = {'Version', 'Name', 'Branch', 'IsRuntime', 'Url', 'Title', 'Comment',
                 'Description', 'Icon', 'Homepage', 'SuggestRemoteName', 'RuntimeRepo',
                 'GPGKey', 'DeployCollectionID'}
    extra = set(s) - supported
    if extra:
        raise ValueError(_('Reference options not supported yet: {options}').format(options=', '.join(sorted(extra))))
    app_id = s.get('Name', '')
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]*(?:\.[A-Za-z_][A-Za-z0-9_-]*){2,}', app_id):
        raise ValueError(_('Invalid application identifier.'))
    if s.get('IsRuntime', 'false') != 'false':
        raise ValueError(_('This interface is intended for applications.'))
    branch = s.get('Branch', 'master')
    if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*', branch):
        raise ValueError(_('Invalid application branch.'))
    # Reject routing escape sequences instead of interpreting them differently from GKeyFile.
    for key in ('Url', 'RuntimeRepo', 'SuggestRemoteName', 'DeployCollectionID'):
        if '\\' in s.get(key, ''):
            raise ValueError(_('Field {key} contains an unsupported escape.').format(key=key))
    source = https_url(s.get('Url', ''))
    runtime = https_url(s['RuntimeRepo']) if s.get('RuntimeRepo') else ''
    spec = RemoteSpec(source, s.get('SuggestRemoteName', app_id.lower()),
                      s.get('Title', app_id), gpg_key(s.get('GPGKey', '')),
                      s.get('DeployCollectionID', ''))
    icon = s.get('Icon', '')
    icon = icon if re.fullmatch(r'[A-Za-z0-9_.-]+', icon) else ''
    return Reference(raw, app_id, s.get('Title', '').strip() or app_id, branch, spec, runtime, icon)


def read_reference(path):
    path = Path(path)
    if path.suffix.lower() != '.flatpakref':
        raise ValueError(_('Select a .flatpakref file.'))
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError(_('Select a regular local file.'))
        return parse_reference(stream.read(LIMIT + 1))


def parse_runtime_repo(raw, descriptor):
    s = section_from_bytes(raw, 'Flatpak Repo')
    if s.get('Version', '1') != '1':
        raise ValueError(_('Source descriptor version not supported yet.'))
    # Do not silently ignore settings that change security or remote semantics.
    supported = {'Version', 'Url', 'Title', 'Comment', 'Description', 'Homepage', 'Icon',
                 'GPGKey', 'DeployCollectionID', 'DefaultBranch'}
    extra = set(s) - supported
    if extra:
        raise ValueError(_('Source options not supported yet: {options}').format(options=', '.join(sorted(extra))))
    return RemoteSpec(https_url(s.get('Url', '')), 'runtime', s.get('Title', 'Runtime'),
                      gpg_key(s.get('GPGKey', '')), s.get('DeployCollectionID', ''), descriptor,
                      s.get('DefaultBranch', ''))


APPSTREAM_LIMIT = 128 * LIMIT


class BoundedXML:
    """Bound decompression and reject DTD/entities, including across chunks."""
    def __init__(self, stream, check):
        self.stream, self.check = stream, check
        self.count, self.tail = 0, b''

    def read(self, size=-1):
        self.check()
        data = self.stream.read(min(size if size >= 0 else 65536, 65536))
        self.count += len(data)
        if self.count > APPSTREAM_LIMIT:
            raise ValueError(_('AppStream exceeds the read limit.'))
        scanned = self.tail + data
        if b'<!DOCTYPE' in scanned or b'<!ENTITY' in scanned or b'\x00' in data:
            raise ValueError(_('Unsupported XML declarations.'))
        self.tail = scanned[-16:]
        return data


def localized_text(nodes):
    import locale
    language = (locale.getlocale()[0] or '').replace('_', '-')
    key = '{http://www.w3.org/XML/1998/namespace}lang'
    # Exact locale, same language, untranslated, then another available locale.
    def rank(node):
        lang = node.get(key, '').replace('_', '-')
        return (0 if lang and lang == language else
                1 if lang and language and lang.split('-')[0] == language.split('-')[0] else
                2 if not lang else 3)
    return next((n.text.strip() for n in sorted(nodes, key=rank) if n.text and n.text.strip()), '')


def compact_name(app_id, base, localized):
    """Recognize an expansion only when it spells the known ID's acronym."""
    short = app_id.rsplit('.', 1)[-1]
    words = re.findall(r'[^\W_]+', base, re.UNICODE)
    if (len(short) >= 2 and short.isalpha() and short.isupper()
            and len(words) >= 2 and ''.join(w[0] for w in words).upper() == short):
        return short
    return localized


def component_presentation(component, reference):
    names = component.findall('name')
    name = localized_text(names)
    base = next((n.text.strip() for n in names if not n.get('{http://www.w3.org/XML/1998/namespace}lang') and n.text), '')
    summary = localized_text(component.findall('summary'))
    name = compact_name(reference.app_id, base, name)
    expanded_acronym = name != localized_text(names)
    return {'name': friendly_name(reference.app_id, reference.title, name),
            'description': summary or (base if expanded_acronym else '')}


def appstream_stream_presentation(stream, reference, arch, check=lambda: None):
    """Stream components, freeing each one; never load an entire catalog tree."""
    import xml.etree.ElementTree as ET
    expected = f'app/{reference.app_id}/{arch}/{reference.branch}'
    root = None
    for event, component in ET.iterparse(BoundedXML(stream, check), events=('start', 'end')):
        if root is None:
            root = component
        if event != 'end' or component.tag != 'component':
            continue
        if component.findtext('id') in (reference.app_id, reference.app_id + '.desktop'):
            bundles = [b.text for b in component.findall('bundle') if b.get('type') == 'flatpak']
            if not bundles or expected in bundles:
                return component_presentation(component, reference)
        component.clear()
        root.clear()
    return {}


def appstream_presentation(directory, reference, arch, check=lambda: None):
    """Read only local caches; tolerate missing, corrupt or oversized documents."""
    import gzip
    import xml.etree.ElementTree as ET
    for filename in ('appstream.xml.gz', 'appstream.xml'):
        try:
            opener = gzip.open if filename.endswith('.gz') else open
            with opener(Path(directory) / filename, 'rb') as stream:
                name = appstream_stream_presentation(stream, reference, arch, check)
                if name:
                    return name
        except (OSError, EOFError, ValueError, ET.ParseError):
            continue
    return {}


def installed_appstream_presentation(data, reference, arch, check=lambda: None):
    """libflatpak load_appdata returns compressed XML for the installed ref."""
    import gzip
    import io
    import xml.etree.ElementTree as ET
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
            return appstream_stream_presentation(stream, reference, arch, check)
    except (OSError, EOFError, ValueError, ET.ParseError):
        return {}


# Compatibility helpers for callers which only need the display name.
def appstream_name(*args, **kwargs):
    return appstream_presentation(*args, **kwargs).get('name', '')


def installed_appstream_name(*args, **kwargs):
    return installed_appstream_presentation(*args, **kwargs).get('name', '')


def desktop_presentation(path, app_id=''):
    """Read Name and Comment, never execute or use GenericName as the app name."""
    try:
        with open(path, 'rb') as stream:
            raw = stream.read(LIMIT + 1)
        if len(raw) > LIMIT:
            return {}
        parser = configparser.ConfigParser(interpolation=None, strict=False)
        parser.optionxform = str
        parser.read_string(raw.decode('utf-8'))
        section = parser['Desktop Entry']
        import locale
        lang = locale.getlocale()[0] or ''
        def value(key):
            return next((section[k].strip() for k in (f'{key}[{lang}]', f'{key}[{lang.split("_")[0]}]', key) if section.get(k, '').strip()), '')
        return {'name': compact_name(app_id, section.get('Name', ''), value('Name')),
                'description': value('Comment')}
    except (OSError, UnicodeError, configparser.Error, KeyError):
        return {}
