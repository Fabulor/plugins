namespace eval fabulor::plugins::example_tcl_greeter {
    variable pluginDirectory [file dirname [file normalize [info script]]]
    variable settingsPath [file join $pluginDirectory settings.conf]
    variable targets [dict create]
}

proc fabulor::plugins::example_tcl_greeter::json_unescape {value} {
    set result ""
    set length [string length $value]

    for {set index 0} {$index < $length} {incr index} {
        set character [string index $value $index]
        if {$character ne "\\"} {
            append result $character
            continue
        }

        incr index
        if {$index >= $length} {
            append result "\\"
            break
        }

        set escape [string index $value $index]
        switch -- $escape {
            "\"" { append result "\"" }
            "\\" { append result "\\" }
            "/"  { append result "/" }
            "b"  { append result "\b" }
            "f"  { append result "\f" }
            "n"  { append result "\n" }
            "r"  { append result "\r" }
            "t"  { append result "\t" }
            "u"  {
                set hexadecimal [string range $value [expr {$index + 1}] [expr {$index + 4}]]
                if {[string length $hexadecimal] == 4 && [scan $hexadecimal %x codepoint] == 1} {
                    append result [format %c $codepoint]
                    incr index 4
                } else {
                    append result "u"
                }
            }
            default { append result $escape }
        }
    }

    return $result
}

proc fabulor::plugins::example_tcl_greeter::json_string {eventData key} {
    set pattern [format {"%s"[[:space:]]*:[[:space:]]*"((?:\\.|[^"\\])*)"} $key]
    if {![regexp -- $pattern $eventData ignored value]} {
        return ""
    }
    return [json_unescape $value]
}

proc fabulor::plugins::example_tcl_greeter::target_key {network channel} {
    return [list [string tolower $network] [string tolower $channel]]
}

proc fabulor::plugins::example_tcl_greeter::load_targets {} {
    variable settingsPath
    variable targets

    set targets [dict create]
    if {![file exists $settingsPath]} {
        return
    }

    if {[catch {
        set handle [open $settingsPath r]
        try {
            fconfigure $handle -encoding utf-8 -translation lf
            set contents [read $handle]
        } finally {
            close $handle
        }

        foreach line [split $contents "\n"] {
            if {[string trim $line] eq ""} {
                continue
            }
            if {[catch {llength $line} length] || $length != 2} {
                error "invalid settings entry"
            }
            lassign $line network channel
            dict set targets [target_key $network $channel] [list $network $channel]
        }
    } message]} {
        fabulor::log "Tcl Greeter could not read its settings: $message"
        set targets [dict create]
    }
}

proc fabulor::plugins::example_tcl_greeter::save_targets {} {
    variable settingsPath
    variable targets

    set temporaryPath "$settingsPath.tmp"
    set handle [open $temporaryPath w]
    try {
        fconfigure $handle -encoding utf-8 -translation lf
        foreach target [lsort -dictionary [dict values $targets]] {
            puts $handle $target
        }
    } finally {
        close $handle
    }
    file rename -force $temporaryPath $settingsPath
}

proc fabulor::plugins::example_tcl_greeter::log_usage {} {
    fabulor::log "Usage: /greeter enable <channel> | disable <channel> | status"
}

proc fabulor::plugins::example_tcl_greeter::on_greeter_command {eventData} {
    variable targets

    if {[string tolower [json_string $eventData word1]] ne "greeter"} {
        return continue
    }

    set action [string tolower [json_string $eventData word2]]
    set channel [string trimleft [json_string $eventData word3] ":"]
    set network [json_string $eventData network]

    if {$action in {status list}} {
        if {[dict size $targets] == 0} {
            fabulor::log "Tcl Greeter has no enabled channels."
        } else {
            fabulor::log "Tcl Greeter enabled channels:"
            foreach target [lsort -dictionary [dict values $targets]] {
                lassign $target configuredNetwork configuredChannel
                fabulor::log "  $configuredChannel on $configuredNetwork"
            }
        }
        return consume
    }

    if {$action ni {enable disable} || $channel eq ""} {
        log_usage
        return consume
    }

    if {$network eq ""} {
        fabulor::log "Tcl Greeter needs an active network for this command."
        return consume
    }

    set key [target_key $network $channel]
    if {$action eq "enable"} {
        if {[dict exists $targets $key]} {
            fabulor::log "Tcl Greeter is already enabled for $channel on $network."
            return consume
        }
        dict set targets $key [list $network $channel]
        set result enabled
    } else {
        if {![dict exists $targets $key]} {
            fabulor::log "Tcl Greeter is not enabled for $channel on $network."
            return consume
        }
        set previousTarget [dict get $targets $key]
        dict unset targets $key
        set result disabled
    }

    if {[catch {save_targets} message]} {
        if {$action eq "enable"} {
            dict unset targets $key
        } else {
            dict set targets $key $previousTarget
        }
        fabulor::log "Tcl Greeter could not save its settings: $message"
        return consume
    }

    fabulor::log "Tcl Greeter $result for $channel on $network."
    return consume
}

proc fabulor::plugins::example_tcl_greeter::on_join {eventData} {
    variable targets

    set network [json_string $eventData network]
    set channel [string trimleft [json_string $eventData channel] ":"]
    if {$channel eq ""} {
        set channel [string trimleft [json_string $eventData word3] ":"]
    }

    if {![dict exists $targets [target_key $network $channel]]} {
        return continue
    }

    set prefix [string trimleft [json_string $eventData word1] ":"]
    set separator [string first "!" $prefix]
    if {$separator >= 0} {
        set nickname [string range $prefix 0 [expr {$separator - 1}]]
    } else {
        set nickname $prefix
    }

    set ownNickname [json_string $eventData nick]
    if {$nickname eq "" || [string equal -nocase $nickname $ownNickname]} {
        return continue
    }

    fabulor::send_message $channel "Hello, $nickname!"
    fabulor::log "Tcl Greeter welcomed $nickname in $channel on $network."
    return continue
}

proc init {} {
    fabulor::plugins::example_tcl_greeter::load_targets
    fabulor::register_callback command fabulor::plugins::example_tcl_greeter::on_greeter_command
    fabulor::register_callback server:JOIN fabulor::plugins::example_tcl_greeter::on_join
}
