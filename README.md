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