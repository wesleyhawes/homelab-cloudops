#!/usr/bin/env bash
# Parse playbooks and every implemented role entry point; never execute them.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

(
  cd "$ROOT/semaphore"
  export ANSIBLE_CONFIG="$PWD/ansible.cfg"
  for playbook in ./*.yml; do
    ansible-playbook --syntax-check -i localhost, "$playbook"
  done
)

(
  cd "$ROOT/ansible"
  export ANSIBLE_CONFIG="$PWD/ansible.cfg"
  export ANSIBLE_ROLES_PATH="$PWD/roles"
  ansible-playbook --syntax-check -i localhost, playbooks/operation.yml \
    -e cloudops_role=nextcloud_aio -e cloudops_operation=check

  # The operation playbook uses dynamic include_role. Static imports make
  # syntax-check also inspect each role's task file without launching a task.
  role_check="$(mktemp "${TMPDIR:-/tmp}/cloudops-ansible-XXXXXX.yml")"
  trap 'rm -f -- "$role_check"' EXIT
  cat > "$role_check" <<'YAML'
---
- name: Parse all implemented provider operations
  hosts: localhost
  gather_facts: false
  tasks:
YAML
  for tasks in roles/nextcloud_aio/tasks/*.yml; do
    operation="$(basename "$tasks" .yml)"
    cat >> "$role_check" <<YAML
    - name: Parse $operation
      ansible.builtin.import_role:
        name: nextcloud_aio
        tasks_from: $operation
YAML
  done
  ansible-playbook --syntax-check -i localhost, "$role_check"
)
