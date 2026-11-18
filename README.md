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
