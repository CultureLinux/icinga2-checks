# Icinga2 (Nagios) checks
## check_systemd
### hosts
    object Host "YOUR_HOSTNAME" {
        import "generic-host"
        ...
        vars.systemd = [ "sshd" , "icinga2" , "crond"]
    }
### service & command 
    apply Service "systemd" {
    import "generic-service"
    check_command = "check_systemd"
    command_endpoint = host.vars.client_endpoint
    vars.systemd_name = host.vars.systemd
    assign where host.vars.client_endpoint && host.vars.os == "Linux" 
    }

    object CheckCommand  "check_systemd" {
        import "plugin-check-command"
        command = [PluginDir + "/check_systemd"]
        
        vars.array_pass = "$systemd_name$"
        arguments = {
        "-s" = { value = "$array_pass$"}
        }
    }

## check_openssl_certificate
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