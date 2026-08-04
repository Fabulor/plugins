namespace eval fabulor::plugins::example_tcl_greeter {
    variable reportedFirstMessage 0
}

proc fabulor::plugins::example_tcl_greeter::on_message {eventData} {
    variable reportedFirstMessage

    if {$reportedFirstMessage} {
        return
    }

    set reportedFirstMessage 1
    array set user [fabulor::get_user_info]
    set location "the active session"
    if {[info exists user(channel)] && $user(channel) ne ""} {
        set location $user(channel)
    }

    fabulor::log "Tcl sample observed its first incoming message event in $location."
}

proc init {} {
    array set user [fabulor::get_user_info]
    set nick "unknown"
    if {[info exists user(nick)] && $user(nick) ne ""} {
        set nick $user(nick)
    }

    fabulor::log "Hello, $nick. Tcl sample ready."
    fabulor::register_callback message fabulor::plugins::example_tcl_greeter::on_message
}
