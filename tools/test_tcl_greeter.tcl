namespace eval fabulor {
    variable logs {}
    variable sent {}
    variable callbacks [dict create]

    proc log {message} {
        variable logs
        lappend logs $message
    }

    proc send_message {target message} {
        variable sent
        lappend sent [list $target $message]
    }

    proc get_user_info {} {
        return [list nick Barry channel #test server irc.example network DALnet]
    }

    proc register_callback {event handler} {
        variable callbacks
        dict set callbacks $event $handler
    }
}

proc assert_equal {actual expected message} {
    if {$actual ne $expected} {
        error "$message: expected <$expected>, got <$actual>"
    }
}

set repositoryRoot [file normalize [file join [file dirname [info script]] ..]]
set temporaryHandle [file tempfile settingsPath]
close $temporaryHandle
file delete $settingsPath

source [file join $repositoryRoot example.tcl.greeter plugin.tcl]
namespace eval fabulor::plugins::example_tcl_greeter [list set settingsPath $settingsPath]
init

assert_equal [lsort [dict keys $fabulor::callbacks]] \
    [lsort {command server:JOIN}] "registered callbacks"

set commandHandler [dict get $fabulor::callbacks command]
set joinHandler [dict get $fabulor::callbacks server:JOIN]

assert_equal [$commandHandler \
    {"network":"DALnet","word1":"VERSION","word2":""}] continue \
    "unrelated command continuation"

set result [$commandHandler \
    {"network":"DALnet","word1":"GREETER","word2":"enable","word3":"#test"}]
assert_equal $result consume "enable consumption"
assert_equal [file exists $settingsPath] 1 "settings persistence"

$joinHandler \
    {"network":"DALnet","channel":"#test","nick":"Barry","word1":":DalBot!bot@example","word3":"#test"}
$joinHandler \
    {"network":"Libera.Chat","channel":"#test","nick":"Barry","word1":":WrongNet!bot@example","word3":"#test"}
assert_equal $fabulor::sent [list [list "#test" "Hello, DalBot!"]] \
    "network isolation"

$commandHandler \
    {"network":"Libera.Chat","word1":"GREETER","word2":"enable","word3":"#test"}
$joinHandler \
    {"network":"Libera.Chat","channel":"#test","nick":"Barry","word1":":LiberaBot!bot@example","word3":"#test"}
assert_equal [lindex $fabulor::sent end] [list "#test" "Hello, LiberaBot!"] \
    "second network greeting"

$commandHandler \
    {"network":"Libera.Chat","word1":"GREETER","word2":"disable","word3":"#test"}
$joinHandler \
    {"network":"Libera.Chat","channel":"#test","nick":"Barry","word1":":DisabledBot!bot@example","word3":"#test"}
assert_equal [llength $fabulor::sent] 2 "disabled target"

$joinHandler \
    {"network":"DALnet","channel":"#test","nick":"Barry","word1":":Barry!user@example","word3":"#test"}
assert_equal [llength $fabulor::sent] 2 "own JOIN suppression"

namespace eval fabulor::plugins::example_tcl_greeter { set targets [dict create] }
fabulor::plugins::example_tcl_greeter::load_targets
assert_equal [dict values $fabulor::plugins::example_tcl_greeter::targets] \
    {{DALnet #test}} "settings reload"

file delete $settingsPath
