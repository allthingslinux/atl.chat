use strict;
use warnings;
use lib 't';

use TestConnection;
use Test::More;

my @users = (
    'one',
    'two',
    'three',
    'four',
    'five',
    'six',
);

plan tests => scalar(@users) + 3;

foreach my $username (@users) {
    my $conn = TestConnection->new($username);

    $conn->reg_cb(session_ready => sub {
        $conn->cond->send;
    });

    my $error = $conn->cond->recv;
    ok(! $error) or diag("$username login failed: $error");
}

do {
    my $conn = TestConnection->new('one', password => '23451');

    $conn->reg_cb(session_ready => sub {
        $conn->cond->send;
    });

    my $error = $conn->cond->recv;
    ok($error);
};

do {
    my $conn = TestConnection->new('invalid', password => '12345');

    $conn->reg_cb(session_ready => sub {
        $conn->cond->send;
    });

    my $error = $conn->cond->recv;
    ok($error);
};

do {
    my $conn = TestConnection->new('seven', password => '1234567');

    $conn->reg_cb(session_ready => sub {
        $conn->cond->send;
    });

    my $error = $conn->cond->recv;
    ok($error);
};
