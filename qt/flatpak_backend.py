"""libflatpak 1.16 adapter. All methods run on the transaction worker."""
import re
import tempfile
from dataclasses import replace
import urllib.request
import gi
gi.require_version('Flatpak', '1.0')
gi.require_version('OSTree', '1.0')
from gi.repository import Flatpak, Gio, GLib, OSTree
from backend import OriginConflict
from metadata import LIMIT, https_url, parse_runtime_repo
from i18n import _


class HttpsOnly(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        https_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class FlatpakDriver:
    def __init__(self):
        self.cancellable = Gio.Cancellable.new()
        self.key_cache = {}
        self.pinned_remotes = {}

    def cancel(self):
        self.cancellable.cancel()

    def prepare(self, reference, scope):
        if scope not in ('user', 'system') and not scope.startswith('system:'):
            raise ValueError(_('Choose where to install.'))
        self.scope = scope
        self.installation = (Flatpak.Installation.new_user(self.cancellable) if scope == 'user'
                             else Flatpak.Installation.new_system(self.cancellable) if scope == 'system'
                             else Flatpak.Installation.new_system_with_id(scope[7:], self.cancellable))
        self.arch = getattr(reference, 'arch', '') or Flatpak.get_default_arch()
        self.full_ref = f'app/{reference.app_id}/{self.arch}/{reference.branch}'
        self.expected_remote = None

    def inventory(self, reference):
        rows = []
        for scope in ('user', 'system'):
            try:
                inst = (self.installation if self.scope == scope else
                        Flatpak.Installation.new_user(self.cancellable) if scope == 'user' else
                        Flatpak.Installation.new_system(self.cancellable))
                apps = [_('{ref} (source {origin})').format(ref=r.format_ref(), origin=r.get_origin())
                        for r in inst.list_installed_refs(self.cancellable)
                        if r.get_name() == reference.app_id]
                remotes = [f'{r.get_name()}: {r.get_url()}' for r in inst.list_remotes(self.cancellable)]
                rows.append(f'{scope}: ' + ('; '.join(apps) or _('application absent')) + '\n' +
                            _('Sources: {list}').format(list='; '.join(remotes) or _('none')))
            except GLib.Error as exc:
                if scope == self.scope:
                    raise
                rows.append(_('{scope}: could not query: {error}').format(scope=scope, error=exc))
        return '\n'.join(rows)

    def installed_ref(self, reference):
        self.installation.drop_caches(self.cancellable)
        return self.installation.get_installed_ref(Flatpak.RefKind.APP, reference.app_id,
                                                   self.arch, reference.branch, self.cancellable)

    def is_installed(self, reference):
        try:
            self.installed_ref(reference)
            return True
        except GLib.Error as exc:
            if exc.matches(Flatpak.error_quark(), Flatpak.Error.NOT_INSTALLED):
                return False
            raise

    def key_fingerprints(self, data):
        if data not in self.key_cache:
            # Decode using the installed OpenPGP implementation in a throwaway
            # repository. Never import keys into the user's keyring to compare.
            with tempfile.TemporaryDirectory(prefix='mainuan-keycheck-') as folder:
                repo = OSTree.Repo.new(Gio.File.new_for_path(folder))
                repo.create(OSTree.RepoMode.BARE_USER_ONLY, self.cancellable)
                repo.remote_add('keycheck', 'https://example.invalid', None, self.cancellable)
                repo.remote_gpg_import('keycheck', Gio.MemoryInputStream.new_from_bytes(
                    GLib.Bytes.new(data)), None, self.cancellable)
                self.key_cache[data] = self.repo_fingerprints(repo, 'keycheck')
                if not self.key_cache[data]:
                    raise OriginConflict(_('The source does not contain a valid signing key.'))
        return self.key_cache[data]

    def repo_fingerprints(self, repo, name):
        result = repo.remote_get_gpg_keys(name, None, self.cancellable)
        if not result[0]:
            raise OriginConflict(_('Could not verify the source keys.'))
        keys = []
        for key in result[1]:
            subkeys, _, _ = key.unpack()
            if not subkeys:
                continue
            primary = subkeys[0]
            if any(primary.get(flag) for flag in ('invalid', 'revoked', 'expired')):
                raise OriginConflict(_('The source contains an invalid, revoked or expired key.'))
            keys.append(primary['fingerprint'])
        return tuple(sorted(keys))

    def repository(self):
        repo = OSTree.Repo.new(self.installation.get_path().get_child('repo'))
        repo.open(self.cancellable)
        return repo

    def remote_signature(self, remote):
        verify = remote.get_gpg_verify()
        return (remote.get_url(), verify, remote.get_collection_id() or '',
                remote.get_disabled(), remote.get_filter() or '', remote.get_nodeps(),
                remote.get_noenumerate(), remote.get_default_branch() or '', remote.get_prio(),
                self.repo_fingerprints(self.repository(), remote.get_name()) if verify else ())

    def check_remote(self, remote, spec=None):
        signature = self.remote_signature(remote)
        url, verify, collection, disabled, filter_path, nodeps, noenumerate, branch, priority, keys = signature
        if not verify:
            raise OriginConflict(_('The source has GPG verification disabled.'))
        if disabled or filter_path:
            raise OriginConflict(_('The configured source is disabled or has a filter. '
                                   'Its configuration must be checked before installing.'))
        if spec:
            if url != spec.url or (spec.collection and spec.collection != collection):
                raise OriginConflict(_('The identity of the configured source differs from the reference.'))
            if spec.key and (not verify or self.key_fingerprints(spec.key) != keys):
                raise OriginConflict(_('The signing key of the configured source differs from the reference.'))
            if spec.default_branch and spec.default_branch != branch:
                raise OriginConflict(_('The source configuration differs from the provided descriptor.'))
        name = remote.get_name()
        if name in self.pinned_remotes and self.pinned_remotes[name] != signature:
            raise OriginConflict(_('The source configuration changed during the installation. Try again.'))
        self.pinned_remotes[name] = signature
        return name

    def remote_candidates(self, spec):
        self.installation.drop_caches(self.cancellable)
        matching = [r for r in self.installation.list_remotes(self.cancellable) if r.get_url() == spec.url]
        # Same name/different URL is not a match; same URL/different trust is a
        # conflict, not permission to create a second weaker origin silently.
        names = [self.check_remote(remote, spec) for remote in matching]
        # Aliases with identical URL, trust and behavior are the same choice.
        if len(names) > 1 and len({self.pinned_remotes[n] for n in names}) == 1:
            return [spec.suggested if spec.suggested in names else sorted(names)[0]]
        return names

    def dependency_candidates(self, names):
        checked = [self.check_remote(self.installation.get_remote_by_name(n, self.cancellable)) for n in names]
        if len(checked) > 1 and len({self.pinned_remotes[n] for n in checked}) == 1:
            return [sorted(checked)[0]]
        return checked

    def remote_description(self, name):
        remote = self.installation.get_remote_by_name(name, self.cancellable)
        return f'{name} — {remote.get_url()}'

    def merge_descriptors(self, first, second):
        if (first.collection and second.collection and first.collection != second.collection
                or first.default_branch and second.default_branch and first.default_branch != second.default_branch
                or first.key and second.key and self.key_fingerprints(first.key) != self.key_fingerprints(second.key)):
            raise OriginConflict(_('The descriptors of the same source have incompatible configurations.'))
        return replace(first, key=first.key or second.key, collection=first.collection or second.collection,
                       default_branch=first.default_branch or second.default_branch)

    def validate_operations(self, ops, reference, main_remote):
        self.installation.drop_caches(self.cancellable)
        expected = f'app/{reference.app_id}/{self.arch}/{reference.branch}'
        for op in ops:
            parsed = Flatpak.Ref.parse(op['ref'])
            if op['type'] not in ('install', 'update'):
                raise OriginConflict(_('The installation would require a change that was not authorized.'))
            if parsed.get_kind() == Flatpak.RefKind.APP and op['ref'] != expected:
                raise OriginConflict(_('The installation tried to include another unauthorized application.'))
            remote = self.installation.get_remote_by_name(op['remote'], self.cancellable)
            self.check_remote(remote, reference.remote if op['ref'] == expected else None)
            if op['ref'] == expected and op['remote'] != main_remote:
                raise OriginConflict(_('The application source changed during the installation.'))
        for name in tuple(self.pinned_remotes):
            self.check_remote(self.installation.get_remote_by_name(name, self.cancellable))

    def installed_locations(self, reference):
        rows = []
        systems = Flatpak.get_system_installations(self.cancellable)
        installations = [('user', Flatpak.Installation.new_user(self.cancellable))]
        self.installations = installations
        installations += [('system' if (i.get_id() or 'default') == 'default' else 'system:' + i.get_id(), i) for i in systems]
        for scope, inst in installations:
            inst.drop_caches(self.cancellable)
            # Enumerate all branches, but actions require an exact reference.

            for ref in inst.list_installed_refs(self.cancellable):
                if ref.get_kind() == Flatpak.RefKind.APP and ref.get_name() == reference.app_id:
                    rows.append({'scope': scope, 'name': ref.get_name(), 'arch': ref.get_arch(),
                                 'branch': ref.get_branch(), 'origin': ref.get_origin(), 'ref': ref.format_ref(),
                                 'displayName': ref.get_appdata_name() or '',
                                 'path': inst.get_path().get_path(), 'selected': ref.format_ref() == self.full_ref})
        return rows

    def system_scopes(self):
        return [{'scope': scope, 'label': inst.get_display_name() or scope}
                for scope, inst in self.installations if scope.startswith('system:')]

    def presentation(self, reference):
        # Optional local metadata only; the worker performs all of this I/O.
        from metadata import appstream_presentation, installed_appstream_presentation, desktop_presentation
        fallback = {'name': reference.display_name, 'description': ''}
        installed_fallback = {}
        for scope, inst in self.installations:
            try:
                refs = inst.list_installed_refs(self.cancellable)
            except Exception:
                continue
            for ref in refs:
                if ref.format_ref() != self.full_ref:
                    continue
                try:
                    name = ref.get_appdata_name()
                    summary = ref.get_appdata_summary()
                    if isinstance(name, str) and name.strip():
                        installed_fallback = {'name': name.strip(), 'description': summary.strip() if isinstance(summary, str) else ''}
                    try:
                        data = ref.load_appdata(self.cancellable)
                        result = installed_appstream_presentation(data.get_data(), reference, self.arch,
                                    self.cancellable.set_error_if_cancelled) if data else {}
                    except Exception:
                        result = {}
                    deploy = ref.get_deploy_dir()
                    desktop = desktop_presentation(str(deploy) + '/files/share/applications/' + reference.app_id + '.desktop', reference.app_id)
                    if result:
                        if desktop.get('name'):
                            result['name'] = desktop['name']
                        return result
                    if desktop.get('name'):
                        return {'name': desktop['name'], 'description': installed_fallback.get('description') or desktop.get('description', '')}
                except Exception:
                    continue
        for scope, inst in self.installations:
            try:
                remotes = inst.list_remotes(self.cancellable)
            except Exception:
                continue
            for remote in remotes:
                try:
                    if remote.get_url() != reference.remote.url:
                        continue
                    path = remote.get_appstream_dir(self.arch)
                    if path:
                        result = appstream_presentation(path.get_path(), reference, self.arch,
                                    self.cancellable.set_error_if_cancelled)
                        if result:
                            return result
                except Exception:
                    continue
        return installed_fallback or fallback

    def presentation_name(self, reference):
        return self.presentation(reference)['name']

    def add_remote(self, spec):
        if not spec.key:
            raise OriginConflict(_('The source does not provide a GPG key; installation stopped.'))
        self.key_fingerprints(spec.key)
        # Never overwrite a remote, even if the supplied suggested name conflicts.
        names = {r.get_name() for r in self.installation.list_remotes(self.cancellable)}
        base = re.sub(r'[^A-Za-z0-9_.-]', '-', spec.suggested).lstrip('-')[:80] or 'mainuan-origin'
        if base in names:
            raise OriginConflict(_('A source with this name and another identity already exists: {name}').format(name=base))
        name = base
        remote = Flatpak.Remote.new(name)
        remote.set_url(spec.url)
        remote.set_title(spec.title)
        remote.set_gpg_verify(bool(spec.key))
        if spec.key:
            remote.set_gpg_key(GLib.Bytes.new(spec.key))
        if spec.collection:
            remote.set_collection_id(spec.collection)
        if spec.default_branch:
            remote.set_default_branch(spec.default_branch)
        if not self.installation.add_remote(remote, False, self.cancellable):
            raise RuntimeError(_('Flatpak did not confirm adding the source.'))
        self.check_remote(self.installation.get_remote_by_name(name, self.cancellable), spec)
        return name

    def fetch_runtime(self, url):
        # Bounded network I/O with TLS and HTTPS-only redirects; no install side effects.
        request = urllib.request.Request(url, headers={'User-Agent': 'Mainuan-Flatpak-Installer/1.1'})
        with urllib.request.build_opener(HttpsOnly()).open(request, timeout=15) as response:
            https_url(response.url)
            data = response.read(LIMIT + 1)
        if self.cancellable.is_cancelled():
            raise GLib.Error.new_literal(Gio.io_error_quark(), _('Cancelled'), Gio.IOErrorEnum.CANCELLED)
        return parse_runtime_repo(data, url)

    def transaction(self, reference, remote, policy):
        self.expected_remote = remote
        tx = Flatpak.Transaction.new_for_installation(self.installation, self.cancellable)
        tx.add_default_dependency_sources()
        tx.connect('ready-pre-auth', lambda t: policy.guarded(False, policy.ready, t, True))
        tx.connect('ready', lambda t: policy.guarded(False, policy.ready, t))
        tx.connect('add-new-remote', lambda t, *args: policy.guarded(False, policy.new_remote, *args))
        tx.connect('choose-remote-for-ref', lambda t, for_ref, ref, remotes:
                   policy.guarded(-1, policy.choose_remote, ref, remotes))
        tx.connect('operation-error', lambda t, op, error, details:
                   policy.operation_error(op.get_ref(), str(error)))
        tx.connect('new-operation', lambda t, op, progress: policy.guarded(None, self.new_operation, op, progress, policy))
        # No automatic rebase or authenticator installation. These require another explicit flow.
        tx.connect('end-of-lifed-with-rebase', lambda *args: False)
        tx.add_install(remote, self.full_ref, None)
        return tx

    def operations(self, tx):
        result = []
        for op in tx.get_operations():
            remote = op.get_remote() or ''
            try:
                url = self.installation.get_remote_by_name(remote, self.cancellable).get_url() if remote else ''
            except GLib.Error:
                url = _('(source unavailable)')
            result.append({'type': op.get_operation_type().value_nick, 'ref': op.get_ref(),
                           'remote': remote, 'url': url, 'commit': op.get_commit() or '',
                           'download': op.get_download_size(), 'installedSize': op.get_installed_size()})
        return result

    def new_operation(self, op, progress, policy):
        def update(p):
            percent = -1 if p.get_is_estimating() else p.get_progress()
            policy.progress(op.get_ref(), p.get_status() or _('In progress…'), percent)
        progress.set_update_frequency(200)
        progress.connect('changed', lambda p: policy.guarded(None, update, p))
        update(progress)

    def run(self, tx):
        if not tx.run(self.cancellable):
            raise RuntimeError(_('The transaction was not completed.'))

    def verify(self, reference):
        ref = self.installed_ref(reference)
        if not ref.get_commit():
            raise RuntimeError(_('The reference has no confirmed deployment.'))
        if self.expected_remote and ref.get_origin() != self.expected_remote:
            raise RuntimeError(_('The installed source differs from the transaction source.'))
        return {'name': ref.get_name(), 'arch': ref.get_arch(), 'branch': ref.get_branch(),
                'scope': self.scope, 'origin': ref.get_origin(), 'ref': ref.format_ref()}

    def remove(self, installed):
        inst = self.action_installation(installed)
        ref = inst.get_installed_ref(Flatpak.RefKind.APP, installed['name'], installed['arch'],
                                    installed['branch'], self.cancellable)
        if ref.format_ref() != installed['ref']:
            raise OriginConflict(_('The selected reference changed.'))
        tx = Flatpak.Transaction.new_for_installation(inst, self.cancellable)
        # No delete-data, unused cleanup, remote removal or rebase.
        tx.set_disable_prune(True)
        tx.set_disable_related(True)
        tx.set_disable_dependencies(True)
        tx.add_uninstall(installed['ref'])
        errors = []
        tx.connect('operation-error', lambda t, op, error, details: errors.append(str(error)) or False)
        def ready(t):
            return all(op.get_ref() == installed['ref'] and
                       op.get_operation_type() == Flatpak.TransactionOperationType.UNINSTALL
                       for op in t.get_operations())
        tx.connect('ready', ready)
        self.run(tx)
        if errors:
            raise RuntimeError('\n'.join(errors))
        inst.drop_caches(self.cancellable)
        try:
            inst.get_installed_ref(Flatpak.RefKind.APP, installed['name'], installed['arch'],
                                   installed['branch'], self.cancellable)
        except GLib.Error as exc:
            if exc.matches(Flatpak.error_quark(), Flatpak.Error.NOT_INSTALLED):
                return
            raise
        raise RuntimeError(_('The reference is still installed in the selected destination.'))

    def action_installation(self, installed):
        if installed['scope'] == 'user':
            inst = Flatpak.Installation.new_user(self.cancellable)
        elif installed['scope'] == 'system':
            inst = Flatpak.Installation.new_system(self.cancellable)
        else:
            matches = [i for i in Flatpak.get_system_installations(self.cancellable)
                       if 'system:' + i.get_id() == installed['scope']]
            if len(matches) != 1:
                raise OriginConflict(_('Ambiguous or unavailable system installation.'))
            inst = matches[0]
        if installed.get('path') and inst.get_path().get_path() != installed['path']:
            raise OriginConflict(_('The path of the selected installation changed.'))
        inst.drop_caches(self.cancellable)
        return inst

    def launch(self, installed):
        inst = self.action_installation(installed)
        ref = inst.get_installed_ref(Flatpak.RefKind.APP, installed['name'], installed['arch'],
                                    installed['branch'], self.cancellable)
        if not inst.launch(ref.get_name(), ref.get_arch(), ref.get_branch(), None, self.cancellable):
            raise RuntimeError(_('Flatpak did not confirm opening the application.'))

    @staticmethod
    def is_cancelled(exc):
        return isinstance(exc, GLib.Error) and exc.matches(Gio.io_error_quark(), Gio.IOErrorEnum.CANCELLED)

    @staticmethod
    def error_message(exc):
        if isinstance(exc, OriginConflict):
            return str(exc)
        if isinstance(exc, GLib.Error):
            if (exc.matches(Gio.io_error_quark(), Gio.IOErrorEnum.PERMISSION_DENIED)
                    or exc.matches(Gio.dbus_error_quark(), Gio.DBusError.ACCESS_DENIED)
                    or exc.matches(Gio.dbus_error_quark(), Gio.DBusError.AUTH_FAILED)):
                return _('Authorization was denied or cancelled.')
            if any(exc.matches(Gio.io_error_quark(), code) for code in (
                    Gio.IOErrorEnum.NETWORK_UNREACHABLE, Gio.IOErrorEnum.HOST_UNREACHABLE,
                    Gio.IOErrorEnum.HOST_NOT_FOUND, Gio.IOErrorEnum.CONNECTION_REFUSED,
                    Gio.IOErrorEnum.TIMED_OUT, Gio.IOErrorEnum.NOT_CONNECTED)):
                return _('Could not access the source. Check the connection and try again.')
            for code, message in (
                (Flatpak.Error.PERMISSION_DENIED, _('Permission denied for this operation.')),
                (Flatpak.Error.NOT_AUTHORIZED, _('Authorization was denied or cancelled.')),
                (Flatpak.Error.AUTHENTICATION_FAILED, _('Could not authenticate with the source.')),
                (Flatpak.Error.REMOTE_NOT_FOUND, _('The source is not available.')),
                (Flatpak.Error.RUNTIME_NOT_FOUND, _('The required components are not available.')),
                (Flatpak.Error.ALREADY_INSTALLED, _('The application was already installed by another process. Try again.')),
                (Flatpak.Error.DIFFERENT_REMOTE, _('There is an installation from another source in this destination.')),
                (Flatpak.Error.INVALID_REF, _('The Flatpak reference is invalid.')),
                (Flatpak.Error.OUT_OF_SPACE, _('There is not enough space to install.'))):
                if exc.matches(Flatpak.error_quark(), code):
                    return message
            if exc.matches(Gio.io_error_quark(), Gio.IOErrorEnum.BUSY):
                return _('Another installation is in progress. Try again.')
        if isinstance(exc, (TimeoutError, OSError)):
            return _('Could not access the source. Check the connection and the details.')
        return _('Could not complete the operation. See the details.')
