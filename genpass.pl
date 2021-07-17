#! /usr/bin/perl
# genpass.pl: generate argon2id hash from a random password. Can be used
# interactively.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# Copyright (c) 2021, Miquel Lionel <lionel@les-miquelots.net>

use warnings;
use strict;
use File::Copy qw(move);
use Crypt::Argon2 qw/argon2id_pass/;
use Term::ReadKey;
use Term::ANSIColor qw(:constants);
my $salt = `openssl rand 16`;
my $opt = $ARGV[0];

sub FillConfigMk { 
        my $hash = shift;
        $hash =~ s/\$/\\044/g;
        $hash =~ s/\\/\\\\/g;
        my $mkconfig = 'config.mk';
        if (-e $mkconfig){
            open my $in, '<', $mkconfig or die "$!";
                open my $out, '>', "$mkconfig.tmp" or die "$!";
                while (<$in>){
                   s/ARGON2ID_HASH =.*/ARGON2ID_HASH =$hash/gi; 
                   print $out $_;
                }
                close $out;
            close $in;
            move("$mkconfig.tmp", $mkconfig) or die "Uh oh, move failed: $!";
            print "Done modifying $mkconfig\n";
        }
}


if (defined $opt){
   if ($opt eq '-i'){ # interactive
        print "Password: ";
        ReadMode 2;
        my $pass = <STDIN>;
        chomp $pass;
        while (length($pass) < 10){
            print "\nYour password is below 10 characters. Fix this: ";
            $pass = <STDIN>;
            chomp $pass;
        }
        print "\nRetype password: ";
        my $confirm = <STDIN>;
        chomp $confirm;
        my $same = $pass cmp $confirm;
        if (not $same == 0){
            ReadMode 1;
            die "\nPasswords don't match.";
        }
        ReadMode 1;

        print "\n\nWant to see your typed password ? [y/n] : ";
        my $ynchoice = <STDIN>;
        chomp $ynchoice;
        if ($ynchoice eq 'y' or $ynchoice eq 'o'){
            print "\nYour password is ", BOLD, "$pass", RESET;
        }
        my $hash = argon2id_pass($pass, $salt, 3, '32M', 1, 32);
        print "\nThe resulting argon2id hash is: ", BOLD, $hash, RESET, "\n";
        FillConfigMk($hash);
    }
}
else {
    my $pass = `openssl rand -base64 32`;
    chomp $pass;
    print $pass,"\n";
    print argon2id_pass($pass, $salt, 3, '32M', 1, 32); 
}
