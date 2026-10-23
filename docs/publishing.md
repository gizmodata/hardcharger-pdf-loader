# Publishing hardcharger-pdf-loader

For the first publication, sign in to PyPI and add a **pending GitHub publisher** at
<https://pypi.org/manage/account/publishing/> using these exact values:

| PyPI field | Value |
|---|---|
| PyPI project name | `hardcharger-pdf-loader` |
| Owner | `gizmodata` |
| Repository name | `hardcharger-pdf-loader` |
| Workflow name | `ci.yml` |
| Environment name | `pypi` |

“Workflow name” is only the filename, **not** `.github/workflows/ci.yml` or the display name `ci`.
Once the project exists, manage its publishers under **Manage → Publishing** instead.
See PyPI's [pending publisher guide](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
and [publisher field reference](https://docs.pypi.org/trusted-publishers/adding-a-publisher/).

The workflow's `publish-pypi` job uses the matching GitHub environment `pypi` and
`id-token: write`. No PyPI API token or GitHub secret is needed. Configure the repository's
`pypi` environment in GitHub Settings → Environments; restrict deployment tags to `v*`
and add reviewers if you want manual release approval.

After registering the publisher and checking the main-branch CI results:

1. Set the version in `pyproject.toml` and add a matching dated CHANGELOG section.
2. Commit and push the release changes to `main`.
3. Tag that commit, e.g. `git tag v0.1.0`, then `git push origin v0.1.0`.
4. CI runs every test on Python 3.11–3.15, builds the wheel/source distribution, checks their
   metadata, validates the tag against the project version, creates a GitHub Release with
   the CHANGELOG notes and artifacts, then publishes those same artifacts to PyPI.

PyPI badges become available after the first successful publication.
