var BOSH_SERVICE = '/http-bind/';
var show_log = false;

Strophe.addNamespace('C2SSTREAM', 'http://prosody.im/streams/c2s');
Strophe.addNamespace('S2SSTREAM', 'http://prosody.im/streams/s2s');
Strophe.addNamespace('ADMINSUB', 'http://prosody.im/adminsub');
Strophe.addNamespace('CAPS', 'http://jabber.org/protocol/caps');

var localJID = null;
var connection   = null;

var adminsubHost = null;
var adhocControl = new Adhoc('#adhocDisplay', function() {});

function log(msg) {
    var entry = $('<div></div>').append(document.createTextNode(msg));
    $('#log').append(entry);
}

function rawInput(data) {
    log('RECV: ' + data);
}

function rawOutput(data) {
    log('SENT: ' + data);
}

function _cbNewS2S(e) {
    var items, item, entry, tmp, retract, id, jid, infos, info, metadata;
    items = e.getElementsByTagName('item');
    for (i = 0; i < items.length; i++) {
        item = items[i];
        id = item.attributes.getNamedItem('id').value;
        jid = item.getElementsByTagName('session')[0].attributes.getNamedItem('jid').value;
        infos = item.getElementsByTagName('info');

        entry = $('<li id="' + id + '">' + jid + '</li>');
        if (tmp = item.getElementsByTagName('encrypted')[0]) {
            if (tmp.getElementsByTagName('valid')[0]) {
                entry.append('<img src="images/secure.png" title="encrypted (certificate valid)" alt=" (secure) (encrypted)" />');
            } else {
                entry.append('<img src="images/encrypted.png" title="encrypted (certificate invalid)" alt=" (encrypted)" />');
            }
        }
        if (item.getElementsByTagName('compressed')[0]) {
            entry.append('<img src="images/compressed.png" title="compressed" alt=" (compressed)" />');
        }
        metadata = $('<ul/>').css('display', 'none');
        entry.on('click', function() {
            $(this).find("ul").slideToggle();
        });
        metadata.appendTo(entry);
        for (j = 0; j < infos.length; j++) {
            info = infos[j];
            metadata.append('<li><b>' + info.attributes.getNamedItem('name').value + ':</b> ' + info.textContent + '</li>');
        }
        if (infos.length == 0)
            metadata.append('<li>No information available</li>');

        if (items[i].getElementsByTagName('out')[0]) {
            entry.appendTo('#s2sout');
        } else {
            entry.appendTo('#s2sin');
        }
    }
    retract = e.getElementsByTagName('retract')[0];
    if (retract) {
        id = retract.attributes.getNamedItem('id').value;
        $('#' + id).remove();
    }
    return true;
}

function _cbNewC2S(e) {
    var items, item, entry, retract, id, jid, infos, info, metadata;
    items = e.getElementsByTagName('item');
    for (i = 0; i < items.length; i++) {
        item = items[i];
        id = item.attributes.getNamedItem('id').value;
        jid = item.getElementsByTagName('session')[0].attributes.getNamedItem('jid').value;
        infos = item.getElementsByTagName('info');
        entry = $('<li id="' + id + '">' + jid + '</li>');
        if (item.getElementsByTagName('encrypted')[0]) {
            entry.append('<img src="images/encrypted.png" title="encrypted" alt=" (encrypted)" />');
        }
        if (item.getElementsByTagName('compressed')[0]) {
            entry.append('<img src="images/compressed.png" title="compressed" alt=" (compressed)" />');
        }
        metadata = $('<ul/>').css('display', 'none');
        entry.on('click', function() {
            $(this).find("ul").slideToggle();
        });
        metadata.appendTo(entry);
        for (j = 0; j < infos.length; j++) {
            info = infos[j];
            metadata.append('<li><b>' + info.attributes.getNamedItem('name').value + ':</b> ' + info.textContent + '</li>');
        }
        if (infos.length == 0)
            metadata.append('<li>No information available</li>');
        entry.appendTo('#c2s');
    }
    retract = e.getElementsByTagName('retract')[0];
    if (retract) {
        id = retract.attributes.getNamedItem('id').value;
        $('#' + id).remove();
    }
    return true;
}

function _cbAdminSub(e) {
    var node = e.getElementsByTagName('items')[0].attributes.getNamedItem('node').value;
    if (node == Strophe.NS.C2SSTREAM) {
        _cbNewC2S(e);
    } else if (node == Strophe.NS.S2SSTREAM) {
        _cbNewS2S(e);
    }

    return true;
}

function onConnect(status) {
    if (status == Strophe.Status.CONNECTING) {
        log('Strophe is connecting.');
    } else if (status == Strophe.Status.CONNFAIL) {
        alert('Connection failed (Wrong host?)');
        log('Strophe failed to connect.');
        showConnect();
    } else if (status == Strophe.Status.DISCONNECTING) {
        log('Strophe is disconnecting.');
    } else if (status == Strophe.Status.DISCONNECTED) {
        log('Strophe is disconnected.');
        showConnect();
    } else if (status == Strophe.Status.AUTHFAIL) {
        alert('Wrong username and/or password');
        log('Authentication failed');
        if (connection) {
            connection.disconnect();
        }
    } else if (status == Strophe.Status.CONNECTED) {
        log('Strophe is connected.');
        connection.sendIQ($iq({to: connection.domain, type: 'get', id: connection.getUniqueId()}).c('adminsub', {xmlns: Strophe.NS.ADMINSUB})
            .c('adminfor'), function(e) {
                var items;
                var domainpart = Strophe.getDomainFromJid(connection.jid);
                items = e.getElementsByTagName('item');
                if (items.length == 0) {
                    alert("You are not an administrator");
                    connection.disconnect();
                    return false;
                }
                for (i = 0; i < items.length; i++) {
                    var host = $(items[i]).text();
                    $('<option/>').text(host).prop('selected', host == domainpart).appendTo('#host');
                }
                showDisconnect();
                adminsubHost = $('#host').val();
                adhocControl.checkFeatures(adminsubHost,
                    function () { adhocControl.getCommandNodes(function (result) { $('#adhocDisplay').empty(); $('#adhocCommands').html(result); }) },
                    function () { $('#adhocCommands').empty(); $('#adhocDisplay').html('<p>This host does not support commands</p>'); });
                connection.addHandler(_cbAdminSub, Strophe.NS.ADMINSUB + '#event', 'message');
                connection.send($iq({to: adminsubHost, type: 'set', id: connection.getUniqueId()}).c('adminsub', {xmlns: Strophe.NS.ADMINSUB})
                    .c('subscribe', {node: Strophe.NS.C2SSTREAM}));
                connection.send($iq({to: adminsubHost, type: 'set', id: connection.getUniqueId()}).c('adminsub', {xmlns: Strophe.NS.ADMINSUB})
                    .c('subscribe', {node: Strophe.NS.S2SSTREAM}));
                connection.sendIQ($iq({to: adminsubHost, type: 'get', id: connection.getUniqueId()}).c('adminsub', {xmlns: Strophe.NS.ADMINSUB})
                    .c('items', {node: Strophe.NS.S2SSTREAM}), _cbNewS2S);
                connection.sendIQ($iq({to: adminsubHost, type: 'get', id: connection.getUniqueId()}).c('adminsub', {xmlns: Strophe.NS.ADMINSUB})
                    .c('items', {node: Strophe.NS.C2SSTREAM}), _cbNewC2S);
        });
    }
}

function showConnect() {
    $('#login').show();
    $('#menu').hide();
    $('#main').hide();
    $('#s2sin').empty();
    $('#s2sout').empty();
    $('#c2s').empty();
    $('#host').empty();
}

function showDisconnect() {
    $('#s2sList').hide();
    $('#c2sList').hide();
    $('#login').hide();

    $('#menu').show();
    $('#main').show();
    $('#adhoc').show();
}

$(document).ready(function () {
    connection = new Strophe.Connection(BOSH_SERVICE);
    if (show_log) {
        $('#log_container').show();
        connection.rawInput = rawInput;
        connection.rawOutput = rawOutput;
    }

    $("#log_toggle").click(function () {
        $("#log").toggle();
    });

    $('#cred').on('submit', function (event) {
        var button = $('#connect').get(0);
        var jid = $('#jid');
        var pass = $('#pass');
        localJID = jid.get(0).value;

        $('#log').empty();
        connection.connect(localJID, pass.get(0).value, onConnect);
        event.preventDefault();
    });

    $('#logout').click(function (event) {
        connection.disconnect();
        event.preventDefault();
    });

    $('#adhocMenu, #serverMenu, #clientMenu').click(function (event) {
        event.preventDefault();
        var tab = $(this).attr('href');
        $('#main > div').hide();
        $(tab).fadeIn('fast');
    });

    $('#host').on('change', function (event) {
        connection.send($iq({to: adminsubHost, type: 'set', id: connection.getUniqueId()}).c('adminsub', {xmlns: Strophe.NS.ADMINSUB})
            .c('unsubscribe', {node: Strophe.NS.C2SSTREAM}));
        connection.send($iq({to: adminsubHost, type: 'set', id: connection.getUniqueId()}).c('adminsub', {xmlns: Strophe.NS.ADMINSUB})
            .c('unsubscribe', {node: Strophe.NS.S2SSTREAM}));
        adminsubHost = $(this).val();
        adhocControl.checkFeatures(adminsubHost,
            function () { adhocControl.getCommandNodes(function (result) { $('#adhocDisplay').empty(); $('#adhocCommands').html(result); }) },
            function () { $('#adhocCommands').empty(); $('#adhocDisplay').html('<p>This host does not support commands</p>'); });
        $('#s2sin').empty();
        $('#s2sout').empty();
        $('#c2s').empty();
        connection.send($iq({to: adminsubHost, type: 'set', id: connection.getUniqueId()}).c('adminsub', {xmlns: Strophe.NS.ADMINSUB})
            .c('subscribe', {node: Strophe.NS.C2SSTREAM}));
        connection.send($iq({to: adminsubHost, type: 'set', id: connection.getUniqueId()}).c('adminsub', {xmlns: Strophe.NS.ADMINSUB})
            .c('subscribe', {node: Strophe.NS.S2SSTREAM}));
        connection.sendIQ($iq({to: adminsubHost, type: 'get', id: connection.getUniqueId()}).c('adminsub', {xmlns: Strophe.NS.ADMINSUB})
            .c('items', {node: Strophe.NS.S2SSTREAM}), _cbNewS2S);
        connection.sendIQ($iq({to: adminsubHost, type: 'get', id: connection.getUniqueId()}).c('adminsub', {xmlns: Strophe.NS.ADMINSUB})
            .c('items', {node: Strophe.NS.C2SSTREAM}), _cbNewC2S);
    });
});

window.onunload = window.onbeforeunload = function() {
    if (connection) {
        connection.disconnect();
    }
}
