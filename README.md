# Icinga 2 & Nagios checks

Monitor systemd services, TLS certificate expiry, pending package updates, and
memory usage from Icinga 2 or the command line.

## Available checks

| Check | What it monitors |
| --- | --- |
| [`check_systemd`](#check_systemd) | Running and enablement states of one or more systemd units. |
| [`check_openssl_certificate`](#check_openssl_certificate) | Days until the certificate presented by a TLS endpoint expires. |
| [`check_apt_update`](#check_apt_update) | Pending package upgrades on APT-based hosts. |
| [`check_update`](#check_update) | Pending package upgrades via YUM or DNF, with configurable thresholds. |
| [`check_mem.pl`](#check_mempl-and-check_mempy) | Free or used memory, with Nagios performance data. |
| [`check_mem.py`](#check_mempl-and-check_mempy) | Free or used memory on Linux, using `/proc/meminfo`. |
| [`check_compose_update`](#check_compose_update) | Running Compose images that differ from their declared registry references. |

## Usage

Run the command-line examples from the repository root. For the Icinga 2
examples, make the executable plugins available under `PluginDir` on the node
that runs each check. Checks with `command_endpoint` run on the named agent.

The Nagios exit codes are `0` (OK), `1` (WARNING), `2` (CRITICAL), and
`3` (UNKNOWN).

## check_systemd

Check one or more units on a systemd host. Pass one `-s` argument for each unit.

```bash
./check_systemd -s sshd -s icinga2 -s crond
```

### Host variables

Add these variables to an existing host and use the name of its agent endpoint.

    object Host "YOUR_HOSTNAME" {
        import "generic-host"
        ...
        vars.os = "Linux"
        vars.client_endpoint = "YOUR_AGENT_ENDPOINT"
        vars.systemd = [ "sshd" , "icinga2" , "crond"]
    }
### service & command 
    apply Service "systemd" {
    import "generic-service"
    check_command = "check_systemd"
    command_endpoint = host.vars.client_endpoint
    vars.systemd_name = host.vars.systemd
    assign where host.vars.client_endpoint && host.vars.os == "Linux" && host.vars.systemd
    }

    object CheckCommand  "check_systemd" {
        import "plugin-check-command"
        command = [PluginDir + "/check_systemd"]
        
        arguments = {
            "-s" = {
                value = "$systemd_name$"
                repeat_key = true
                required = true
            }
        }
    }

## check_openssl_certificate

Check the expiration date of the certificate presented by a TLS endpoint. The
check returns WARNING with 11–27 whole days left and CRITICAL with 10 or fewer.
It requires OpenSSL, GNU `date`, and `timeout`.

```bash
./check_openssl_certificate example.org 443
```

### hosts
    object Host "HTTPS-hosts" {
        import "generic-host"
        address = "127.0.0.1"

        vars.local.vhosts.ssl["icinga.local.clinux.fr"] = { port = 443 }
        vars.local.vhosts.ssl["proxmox.local.clinux.fr"] = { port = 8006 }
    }
### service & command 
    apply Service "Certificat " for (vhost => config in host.vars.local.vhosts.ssl) {
    import "generic-service"
    check_command = "check_openssl_certificate"

    vars.ssl_port = config.port
    vars.vhost_name = vhost

    assign where host.vars.local.vhosts.ssl
    }

    object CheckCommand "check_openssl_certificate" {
    import "plugin-check-command"
    command = [ PluginDir + "/check_openssl_certificate",
        "$vhost_name$",
        "$ssl_port$"
    ]
    }

## check_apt_update

List packages with available upgrades on a host that uses APT. The check takes
no arguments and returns WARNING when at least one upgrade is available.

```bash
./check_apt_update
```

```icinga2
object CheckCommand "check_apt_update" {
    import "plugin-check-command"
    command = [ PluginDir + "/check_apt_update" ]
}
```

## check_update

Count available upgrades using `yum` (the default) or `dnf`. The default
thresholds are 5 for WARNING and 10 for CRITICAL. The count must exceed a
threshold to trigger that state. The check reports the count as `updates`
performance data.

```bash
./check_update -b yum
./check_update -b dnf -w 5 -c 10
```

```icinga2
object CheckCommand "check_update" {
    import "plugin-check-command"
    command = [ PluginDir + "/check_update" ]
    arguments = {
        "-b" = "$package_update_backend$"
        "-w" = "$package_update_warning$"
        "-c" = "$package_update_critical$"
    }
}
```

## check_mem.pl and check_mem.py

Use `-u` for used memory or `-f` for free memory. The thresholds are
percentages. In used-memory mode, WARNING must be lower than CRITICAL. In
free-memory mode, WARNING must be higher than CRITICAL. Both plugins accept
`-C` to count caches as free. To exclude hugepages from the total, use `-h`
with Perl or `-H` with Python. The Python check reads Linux `/proc/meminfo`.
The Perl check emits memory performance data.

```bash
./check_mem.pl -u -C -w 80 -c 90
./check_mem.py -f -C -w 20 -c 10
```

These Icinga 2 commands use the same used-memory options so each host can
choose a plugin.

```icinga2
template CheckCommand "local-memory-options" {
    import "plugin-check-command"
    arguments = {
        "-w" = "$local_memory_warning$"
        "-c" = "$local_memory_critical$"
    }
    vars.local_memory_warning = 80
    vars.local_memory_critical = 90
}

object CheckCommand "check_mem_pl" {
    import "local-memory-options"
    command = [ PluginDir + "/check_mem.pl", "-u", "-C" ]
}

object CheckCommand "check_mem_py" {
    import "local-memory-options"
    command = [ PluginDir + "/check_mem.py", "-u", "-C" ]
}
```

## Run package and memory checks on Icinga agents

Add the appropriate variables to each existing host definition. These two
examples assume `vars.client_endpoint` names the host's Icinga agent.

```icinga2
// Debian or Ubuntu host
vars.local_plugin_checks = {
    "package-updates" = { check = "check_apt_update" }
    "memory" = { check = "check_mem_py" }
}
```

```icinga2
// RPM-based host
vars.local_plugin_checks = {
    "package-updates" = {
        check = "check_update"
        options = {
            package_update_backend = "dnf"
            package_update_warning = 5
            package_update_critical = 10
        }
    }
    "memory" = { check = "check_mem_pl" }
}
```

Define this service rule once.

```icinga2
apply Service for (service_name => config in host.vars.local_plugin_checks) {
    import "generic-service"
    check_command = config.check
    command_endpoint = host.vars.client_endpoint

    if (config.options) {
        vars += config.options
    }

    assign where host.vars.client_endpoint
}
```

## check_compose_update

Scan a directory for Docker Compose projects and compare each running image
against the declared registry reference for the same platform. The scan stops
descending once it finds a Compose file in a directory. Use a repeatable
`--exclude` for directories outside those projects.

The check requires Python 3, Docker Compose, Buildx, and access to the Docker
Engine and the relevant registries under the account running the check. It
reads image metadata in place. Services with a build configuration or without
an active container are skipped.

The default output shows running containers. Confirmed updates (`!`) appear
first, followed by images using `latest` without a confirmed update (`?`) and
then the remaining results. An image without a tag or digest implicitly uses
`latest`. Both markers trigger WARNING. Pass `--full` for the full inventory,
image digests and cache statistics.

```bash
./check_compose_update --root /home/docky/docker-prod \
  --cache-file "/tmp/compose-update-$UID/registry.sqlite3" --cache-ttl 3600
```

The check creates the cache directory and SQLite database when needed,
including in the default short output mode. Use a separate directory for each
account that runs the check. If the system clears `/tmp`, the next check
rebuilds the cache. The cache stores successful registry digests per image
reference and platform for one hour by default. Local container
images are inspected on every run. An expired entry must be refreshed before
it can be used again. Omit `--cache-file` or set `--cache-ttl 0` to disable
persistent caching. Use `--debug` for Docker diagnostics and
`--registry-budget` to set the total registry time budget in seconds.

### Integrate with an Icinga 2 agent

**1. Prepare the Docker host**

From a checkout on the Docker host, copy the plugin into the agent's
`PluginDir`. The example uses `icinga` and
`/usr/lib64/nagios/plugins`. Substitute the account and directory configured
on your agent.

```bash
check_user=icinga
plugin_dir=/usr/lib64/nagios/plugins
cache_dir=/tmp/icinga2-compose-update

sudo install -m 0755 check_compose_update "$plugin_dir/check_compose_update"
```

The check account needs to traverse the scan root, read the Compose files and
their `.env` files, access Docker as configured for the agent, and write to
the cache directory. Configure any required registry credentials for that same
account.

If the agent uses the standard rootful Docker socket owned by the `docker`
group, add the check account to that group. Membership grants root-level
privileges. [Docker Engine access](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user)

```bash
sudo usermod -aG docker "$check_user"
```

If the scan root is under a private home directory, inspect the permissions on
each path component with `namei -l /home/docky/docker-prod`. Choose one of the
following options to let the check account traverse `/home/docky`.

**Option A — ACL for the check account.** On a filesystem with ACL support,
grant the check account traversal through `/home/docky`:

```bash
sudo setfacl -m "u:${check_user}:--x" /home/docky
```

**Option B — Use the `docky` group.** Add the check account to the group,
and grant the group traversal through `/home/docky`. The account also gains access
to other files and directories already shared with the `docky` group.

```bash
sudo usermod -aG docky "$check_user"
sudo chmod g+x /home/docky
```

With either option, the account still needs read and traverse access to the
directories it scans and read access to the Compose files and their inputs.

After changing group memberships, restart Icinga on the Docker host so the
agent picks them up. Verify Docker access as the check account.

```bash
sudo systemctl restart icinga2
sudo -u "$check_user" docker info
```

**2. Define the check and service**

Put the `CheckCommand` in a global zone shared by the scheduler and the agent
(for example, `zones.d/global-templates/commands.conf` if that zone is configured).
Put the `apply Service` rule in the zone where the Docker host object is
configured. The `command_endpoint` sends execution to the Docker agent.
[Icinga 2 distributed monitoring](https://icinga.com/docs/icinga-2/latest/doc/06-distributed-monitoring/)

```icinga2
object CheckCommand "check_compose_update" {
    import "plugin-check-command"
    command = [ PluginDir + "/check_compose_update" ]
    timeout = 5m
    arguments = {
        "--root" = {
            value = "$compose_update_root$"
            required = true
        }
        "--cache-file" = "$compose_update_cache_file$"
        "--cache-ttl" = "$compose_update_cache_ttl$"
    }
    vars.compose_update_cache_ttl = 3600
}
```

```icinga2
apply Service "compose-image-updates" {
    import "generic-service"
    check_command = "check_compose_update"
    command_endpoint = host.vars.client_endpoint
    check_interval = 30m
    assign where host.vars.client_endpoint && host.vars.compose_update_root
}
```

Add these variables to the existing Docker host object. Set
`client_endpoint` to the exact name of the agent's Icinga `Endpoint`.
The two paths are local to the agent.

```icinga2
vars.client_endpoint = "docker.example.org"
vars.compose_update_root = "/home/docky/docker-prod"
vars.compose_update_cache_file = "/tmp/icinga2-compose-update/registry.sqlite3"
```

**3. Validate the integration**

On the Docker host, run the installed plugin as the check account. The first
run initializes the cache when it is enabled. To inspect cache hit counts,
repeat the command with `--full`. The Icinga service uses the short output
by default.

```bash
sudo -u "$check_user" -- "$plugin_dir/check_compose_update" \
  --root /home/docky/docker-prod \
  --cache-file "$cache_dir/registry.sqlite3"
```

Validate the Icinga configuration before reloading it on the scheduler.
After the first scheduled check, confirm the service result and the update
lines in Icinga Web.

```bash
sudo icinga2 daemon -C
```
