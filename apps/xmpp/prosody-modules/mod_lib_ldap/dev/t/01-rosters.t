use strict;
use warnings;
use lib 't';

use AnyEvent::XMPP::Util qw(split_jid);
use TestConnection;
use Test::More;

sub test_roster {
    my ( $username, $expected_contacts ) = @_;

    local $Test::Builder::Level = $Test::Builder::Level + 1;
    my @contacts;

    my $conn = TestConnection->new($username);

    $conn->reg_cb(roster_update => sub {
        my ( undef, $roster ) = @_;

        @contacts = sort { $a->{'username'} cmp $b->{'username'} } map {
            +{
                username     => (split_jid($_->jid))[0],
                name         => $_->name,
                groups       => [ sort $_->groups ],
                subscription => $_->subscription,
            }
        } $roster->get_contacts;
        $conn->cond->send;
    });

    my $error = $conn->cond->recv;

    if($error) {
        fail($error);
        return;
    }
    @$expected_contacts = sort { $a->{'username'} cmp $b->{'username'} }
        @$expected_contacts;
    foreach my $contact (@$expected_contacts) {
        $contact->{'subscription'} = 'both';
        @{ $contact->{'groups'} } = sort @{ $contact->{'groups'} };
    }
    is_deeply(\@contacts, $expected_contacts);
}

plan tests => 5;

test_roster(one => [{
    username => 'two',
    name     => 'Jane Testerson',
    groups   => ['everyone', 'admin'],
}, {
    username => 'three',
    name     => 'Jerry Testerson',
    groups   => ['everyone'],
}, {
    username => 'four',
    name     => 'Jack Testerson',
    groups   => ['everyone'],
}, {
    username => 'five',
    name     => 'Jimmy Testerson',
    groups   => ['everyone'],
}]);

test_roster(two => [{
    username => 'one',
    name     => 'John Testerson',
    groups   => ['everyone', 'admin'],
}, {
    username => 'three',
    name     => 'Jerry Testerson',
    groups   => ['everyone'],
}, {
    username => 'four',
    name     => 'Jack Testerson',
    groups   => ['everyone'],
}, {
    username => 'five',
    name     => 'Jimmy Testerson',
    groups   => ['everyone'],
}]);

test_roster(three => [{
    username => 'one',
    name     => 'John Testerson',
    groups   => ['everyone'],
}, {
    username => 'two',
    name     => 'Jane Testerson',
    groups   => ['everyone'],
}, {
    username => 'four',
    name     => 'Jack Testerson',
    groups   => ['everyone'],
}, {
    username => 'five',
    name     => 'Jimmy Testerson',
    groups   => ['everyone'],
}]);

test_roster(four => [{
    username => 'one',
    name     => 'John Testerson',
    groups   => ['everyone'],
}, {
    username => 'two',
    name     => 'Jane Testerson',
    groups   => ['everyone'],
}, {
    username => 'three',
    name     => 'Jerry Testerson',
    groups   => ['everyone'],
}, {
    username => 'five',
    name     => 'Jimmy Testerson',
    groups   => ['everyone'],
}]);

test_roster(five => [{
    username => 'one',
    name     => 'John Testerson',
    groups   => ['everyone'],
}, {
    username => 'two',
    name     => 'Jane Testerson',
    groups   => ['everyone'],
}, {
    username => 'three',
    name     => 'Jerry Testerson',
    groups   => ['everyone'],
}, {
    username => 'four',
    name     => 'Jack Testerson',
    groups   => ['everyone'],
}]);
