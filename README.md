# ocp_lab.ai — Ansible collection for the OpenShift Assisted Installer

Ansible modules for the [OpenShift Assisted Installer](https://docs.redhat.com/en/documentation/assisted_installer_for_openshift_container_platform)
REST API, so OpenShift clusters can be defined and installed from playbooks.

> **Status:** just started. Nothing is usable yet — follow the milestones to watch it grow.

## The API we automate

| What | Link |
|---|---|
| Interactive API docs | https://api.openshift.com/?urls.primaryName=assisted-service%20service |
| Machine-readable spec (Swagger 2.0) | https://api.openshift.com/api/assisted-install/v2/openapi |

## How this repo is built

Every change starts as a GitHub issue, is made on a feature branch, and is merged
through a pull request. Each milestone (M00, M01, …) is tagged, so you can check out
any stage and see how the project grew — the history doubles as a tutorial.

## Disclaimer

This is an independent project. It is not affiliated with, endorsed by, or supported
by Red Hat. "OpenShift" is a trademark of Red Hat, Inc.

Contributions are welcome — see the issue tracker once the repository is public.

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
