#! /usr/bin/perl
use warnings;
use strict;
use Crypt::Argon2 qw/argon2id_pass/;
my $pass = `openssl rand -base64 32`;
my $salt = `openssl rand 16`;
chomp $pass;
print "$pass\n";
print argon2id_pass($pass, $salt, 3, '32M', 1, 32),"\n";
