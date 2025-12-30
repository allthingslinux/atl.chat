package TestConnection;

use strict;
use warnings;
use parent 'AnyEvent::XMPP::IM::Connection';

use 5.010;

our $HOST         = 'localhost';
our $TIMEOUT      = 5;
our %PASSWORD_FOR = (
    one   => '12345',
    two   => '23451',
    three => '34512',
    four  => '45123',
    five  => '51234',
    six   => '123456',
    seven => '1234567',
);

sub new {
    my ( $class, $username, %options ) = @_;

    my $cond  = AnyEvent->condvar;
    my $timer = AnyEvent->timer(
        after => $TIMEOUT,
        cb    => sub {
            $cond->send('timeout');
        },
    );

    my $self = $class->SUPER::new(
        username => $username,
        domain   => $HOST,
        password => $options{'password'} // $PASSWORD_FOR{$username},
        resource => 'test bot',
    );

    $self->reg_cb(error => sub {
        my ( undef, $error ) = @_;

        $cond->send($error->string);
    });

    bless $self, $class;

    $self->{'condvar'}       = $cond;
    $self->{'timeout_timer'} = $timer;

    $self->connect;

    return $self;
}

sub cond {
    my ( $self ) = @_;

    return $self->{'condvar'};
}

1;
