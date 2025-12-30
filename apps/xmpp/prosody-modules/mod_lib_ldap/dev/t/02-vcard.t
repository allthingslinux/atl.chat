use strict;
use warnings;
use lib 't';

use TestConnection;
use AnyEvent::XMPP::Ext::VCard;
use MIME::Base64 qw(decode_base64);
use Test::More;

sub test_vcard {
    my ( $username, $expected_fields ) = @_;

    $expected_fields->{'JABBERID'} = $username . '@' . $TestConnection::HOST;
    $expected_fields->{'VERSION'}  = '2.0';

    my $conn  = TestConnection->new($username);
    my $vcard = AnyEvent::XMPP::Ext::VCard->new;

    local $Test::Builder::Level = $Test::Builder::Level + 1;

    $conn->reg_cb(stream_ready => sub {
        $vcard->hook_on($conn);
    });

    $conn->reg_cb(session_ready => sub {
        $vcard->retrieve($conn, undef, sub {
            my ( $jid, $vcard, $error ) = @_;

            if(eval { $vcard->isa('AnyEvent::XMPP::Error') }) {
                $error = $vcard;
            }

            if($error) {
                $conn->cond->send($error->string);
                return;
            }

            delete $vcard->{'_avatar_hash'}; # we don't check this
            delete $vcard->{'PHOTO'};        # PHOTO data is treated specially
                                             # by the vCard extension

            foreach my $key (keys %$vcard) {
                my $value = $vcard->{$key};

                $value = $value->[0] if ref($value) eq 'ARRAY';

                if($value eq '') {
                    delete $vcard->{$key};
                } else {
                    $vcard->{$key} = $value;
                }
            }

            is_deeply $vcard, $expected_fields or diag(explain($vcard));
            $conn->cond->send;
        });
    });

    my $error = $conn->cond->recv;

    if($error) {
        fail($error);
        return;
    }
}

plan tests => 5;

my $photo_data = do {
    local $/;
    my $data = <DATA>;
    chomp $data;

    decode_base64($data)
};

test_vcard(one => {
    FN       => 'John Testerson',
    NICKNAME => 'one',
    TEL      => {
        NUMBER => '555-555-5555',
        WORK   => '',
        VOICE  => '',
    },
});

test_vcard(two => {
    FN       => 'Jane Testerson',
    NICKNAME => 'two',
    TEL      => {
        NUMBER => '',
        WORK   => '',
        VOICE  => '',
    },
});

test_vcard(three => {
    FN       => 'Jerry Testerson',
    NICKNAME => 'three',
    TEL      => {
        NUMBER => '',
        WORK   => '',
        VOICE  => '',
    },
});

test_vcard(four => {
    FN       => 'Jack Testerson',
    NICKNAME => 'four',
    TEL      => {
        NUMBER => '',
        WORK   => '',
        VOICE  => '',
    },
});

test_vcard(five => {
    FN       => 'Jimmy Testerson',
    NICKNAME => 'five',
    TEL      => {
        NUMBER => '',
        WORK   => '',
        VOICE  => '',
    },
    _avatar      => $photo_data,
    _avatar_type => 'image/jpeg',
});

__DATA__
/9j/4AAQSkZJRgABAQAAAQABAAD//gA+Q1JFQVRPUjogZ2QtanBlZyB2MS4wICh1c2luZyBJSkcg
SlBFRyB2NjIpLCBkZWZhdWx0IHF1YWxpdHkK/9sAQwAIBgYHBgUIBwcHCQkICgwUDQwLCwwZEhMP
FB0aHx4dGhwcICQuJyAiLCMcHCg3KSwwMTQ0NB8nOT04MjwuMzQy/9sAQwEJCQkMCwwYDQ0YMiEc
ITIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIy/8AAEQgA
yADIAwEiAAIRAQMRAf/EAB8AAAEFAQEBAQEBAAAAAAAAAAABAgMEBQYHCAkKC//EALUQAAIBAwMC
BAMFBQQEAAABfQECAwAEEQUSITFBBhNRYQcicRQygZGhCCNCscEVUtHwJDNicoIJChYXGBkaJSYn
KCkqNDU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6g4SFhoeIiYqSk5SVlpeY
mZqio6Slpqeoqaqys7S1tre4ubrCw8TFxsfIycrS09TV1tfY2drh4uPk5ebn6Onq8fLz9PX29/j5
+v/EAB8BAAMBAQEBAQEBAQEAAAAAAAABAgMEBQYHCAkKC//EALURAAIBAgQEAwQHBQQEAAECdwAB
AgMRBAUhMQYSQVEHYXETIjKBCBRCkaGxwQkjM1LwFWJy0QoWJDThJfEXGBkaJicoKSo1Njc4OTpD
REVGR0hJSlNUVVZXWFlaY2RlZmdoaWpzdHV2d3h5eoKDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ip
qrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uLj5OXm5+jp6vLz9PX29/j5+v/aAAwDAQACEQMR
AD8A9/opM0ZFADVGGan00feNLkUALSGkJqjfX5t4jsjkZyDtwuRmhK4m0ldl4sBnNZk+sRCJnt0a
cqdoC/xH0FYM+t363cPlxyPCv+sDYBfPXgdMdqoXGtxRXxuZftMSxMypAkXBXuST3JreNB9TnliI
9GaNz4jvYpQk6wwCQ7UAcMwPoazrjUJpmO+Rm+prjtZ1Zb7UZLiOLyQcYA68dz71qWV99qtEkJ+b
7rc9xXq4ehFK9tTzsVOT1voaDszdTgVUlnVBhT/9eoZrgngVXLHOTXao2OBslLljk0hmx3qBn5zm
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
