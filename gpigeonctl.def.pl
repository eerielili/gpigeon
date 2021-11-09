#! /usr/bin/perl -T
# gpigeonctl: user, cookies and GPG key management for gpigeon.cgi

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

# Copyright (c) 2020-2021, Miquel Lionel <lionel@les-miquelots.net>

use warnings;
use strict;
use Email::Valid;
use Term::ReadKey;
use Crypt::Argon2 qw(argon2id_pass);
use DBI;
delete @ENV{qw(IFS PATH CDPATH BASH_ENV)};
$ENV{'PATH'} = q{bin_path_goes_here};
my $dbh_path = q{db_path_goes_here};
my $cookiesdir = q{cookies_dir_goes_here};
my $GNUPGHOME = q{gpgdir_goes_here};
my $web_user = q{web_user_goes_here};
my $web_dir = q{web_dir_goes_here};
my ($escaddr, $ynchoice) = undef;
my $opt = $ARGV[0];
my $version = 0.1;
my $dbh = DBI->connect("DBI:SQLite:dbname=$dbh_path", undef, undef,
{ RaiseError => 1,
AutoCommit => 1,
})
or die $DBI::errstr;


sub DbGetLine {
    my ($dbh, $query) = @_;
    my $prep = $dbh->prepare( $query );
    my $exec = $prep->execute() or die $DBI::errstr;

    if ($exec < 0){
        print $DBI::errstr;
    }

    while (my @rows = $prep->fetchrow_array()) {
        my $row = $rows[0];
        return $row;
    }
}

sub ListUsers {
    my ($dbh, $query) = @_;
    my $prep = $dbh->prepare( $query );
    my $exec = $prep->execute() or die $DBI::errstr;

    if ($exec < 0){
        print $DBI::errstr;
    }

    while (my @rows = $prep->fetchrow_array()) {
       print "$row[0]\t$rows[1]"; 
    }
}


sub RecursiveChown {
    my ($junk, $junk2, $uid, $gid) = getpwnam($web_user);
    if ($_ =~ qr|^([-+@\w./]+)$|){ # pattern taken from File::Find
        chown $uid, $gid, "$1";
    }
}

sub DeleteCookies {
    if ($_ =~ /^([\w]+)\.txt$/){
        unlink "$1.txt";
    }
}

sub EscapeArobase {
    my $esc = shift;
    if ($esc =~ /^([-\@\w.]+)$/) {
        $esc = $1;                     # $data now untainted
	$esc =~ s/@/\\@/;
	return $esc;
    } else {
        die "\n";      # log this somewhere
    }
}

sub PrintHelp{
	print 'Copyright (c) 2020-2021, Miquel Lionel <lionel@les-miquelots.net>',"\n\n";
	print 'usage: gpigeonctl [init] [adduser] [deluser] [cleancookies] [cleanlinks] [version]', "\n";
    exit 0;
}

sub SetMail {
    print "Mail address: ";
    my $addr = <STDIN>;
    if (not Email::Valid->address($addr)){
        die "\nNot a valid email address.";
    }
	chomp $addr;
	return $addr;
}

sub SetNick {
	my $addr = shift;
    print "\nNickname (optional): ";
    my $nick = <STDIN>;
    chomp $nick;
    if (length($nick) eq 0){
        $nick = $addr;
        return $nick;
    }
    elsif (defined $nick and not $nick =~ /^([\w]+)$/){
        die "\nYour nickname must have only alphanumeric characters.\n";
    }
	return $nick;
}

sub SetPasswd {
    ReadMode 2;
    print "\nPassword: ";
    my $pass = <STDIN>;
    if (not length($pass) > 10){
        ReadMode 1;
        die "\nFor your safety, you should have a password at least 10 characters long.\n";
    }
    ReadMode 1;
    chomp $pass;
    my $salt = `openssl rand 16`;
    my $hash = argon2id_pass($pass, $salt, 3, '32M', 1, 32);
}

sub TransferGPGPubKey {
	my ($addr, $GNUPGHOME) = @_;
	my $escaddr = EscapeArobase($addr);
    my $gpgid = '0x'.`gpg --with-colons -k $escaddr | grep "pub:u" | cut -d':' -f5`;
    chomp $gpgid;
    if (not $gpgid =~ /^([\w]+)$/ and not length($gpgid) eq 18){
        die "\nYour GPG 0xlong key id is not a correct one. It seems that no public key was tied to the provided e-mail address.\n";
    }
    else{
        $gpgid = $1;
        print "\nGPG ID: $gpgid\n";
        return $gpgid;
    }
}

# i should use a module for this lol
if (defined $opt){

    if($opt eq 'init'){
        if ( -e $dbh_path){
            print "The database already exist at $dbh_path.\n";
            print "Overwrite ? [y/n] ";
            $ynchoice = <STDIN>;
            chomp $ynchoice;
            if ($ynchoice eq 'o' or $ynchoice eq 'y'){
                unlink $dbh_path;
                print "Done.\n";
            }
        } 
        
        if (-d $GNUPGHOME){
            use File::Path qw/rmtree/;
            print "GPG home directory already exists at $GNUPGHOME. Delete it ? [y/n] ";
            $ynchoice = <STDIN>;
            chomp $ynchoice;
            if ($ynchoice eq 'o' or $ynchoice eq 'y'){
               rmtree($GNUPGHOME); 
               print "Done.\n";
            }

        }
        

        my $addr = SetMail();
        my $nick = SetNick($addr);
        my $hash = SetPasswd();
        my $gpgid = TransferGPGPubKey($addr,$GNUPGHOME);
        my ($junk, $junk2, $uid, $gid) = getpwnam($web_user);
            use File::Path qw/make_path/;
	        make_path($GNUPGHOME);
            chmod(0700,$GNUPGHOME);
            open my $out, '>', "$GNUPGHOME/gpg.conf" or die $!;
                print $out "use-agent\n";
                print $out "charset utf-8\n";
                print $out "no-escape-from-lines\n";
                print $out "trust-model always\n";
                print $out "personal-digest-preferences SHA512 SHA384 SHA256 SHA224\n";
                print $out "default-preference-list SHA512 SHA384 SHA256 SHA224 AES256 AES192 AES CAST5 BZIP2 ZLIB ZIP Uncompressed";
            close $out;
        use GPG;
        `gpg -a --export $gpgid > key.asc`;
        `gpg --homedir $GNUPGHOME --import key.asc`;
        my $gpg =  new GPG(gnupg_path => "/usr/bin", homedir => "$GNUPGHOME");
        my $enc_msg = $gpg->encrypt("test", $gpgid)
              or die "\nOops, it seems gpg won't encrypt the test message. Here's why :\n",$gpg->error();

        my $dbh = DBI->connect("DBI:SQLite:dbname=$dbh_path", undef, undef,
            { 
            RaiseError => 1,
            AutoCommit => 1,
            }) or die $DBI::errstr;
        $dbh->do('create table users (userid integer primary key, mail text NOT NULL UNIQUE, name text UNIQUE, pass text NOT NULL, gpgfp text NOT NULL UNIQUE, isadmin integer NOT NULL)') or die $DBI::errstr;
        $dbh->do('create index idx_usersid on users(userid)') or die $DBI::errstr;
        $dbh->do(qq{INSERT INTO users VALUES( ?, '$addr', '$nick', '$hash', '$gpgid', 1)}) or die $DBI::errstr;
        $dbh->disconnect;
        unlink 'key.asc';
        find(\&recursivechown, $cookiesdir);
        find(\&recursivechown, $GNUPGHOME);
        chown $uid, $gid, $dbh_path;
        print "\nThe database has been initialized.\n";
        exit 0;
    }

	if ($opt eq 'adduser'){
		if (not -e $dbh_path){
			print "It seems that the database doesn't exist. Type `gpigeonctl init' in a terminal to create it.\n";
			exit 1;
		}
        
		my $addr = SetMail();
		my $nick = SetNick($addr);
		my $hash = SetPasswd();
		my $gpgid = TransferGPGPubKey($addr,$GNUPGHOME);

		my $dbh = DBI->connect("DBI:SQLite:dbname=$dbh_path", undef, undef,
		{ RaiseError => 1,
		AutoCommit => 1,
		})
		or die $DBI::errstr;
		$dbh->do(qq{INSERT INTO users VALUES( ?, '$addr', '$nick', '$hash', '$gpgid', 1)}) or die $DBI::errstr;
		$dbh->disconnect;
		print "\nUser $addr added succesfully\n";	
		exit 0;
	}

	if ($opt eq 'deluser'){
		use File::Path qw/rmtree/;
		my $addr = SetMail();
		my $esc = EscapeArobase($addr);
        my $uid = DbGetLine($dbh, "SELECT userid FROM users WHERE mail='$esc'") or die "$!";
		$dbh->do(qq{DELETE FROM users where mail='$addr'}) or die $DBI::errstr;
		$dbh->disconnect;
        if (defined $uid and $uid > 0){
            rmtree("$cookiesdir/$uid", "$web_dir/l/$uid", 
                    { verbose => 1,
                      safe => 1
            });
            #GPG module doesn't delete key
            `GNUPGHOME="$GNUPGHOME" gpg --yes --batch --delete-key $esc`;
        }
		print "\nUser $addr deleted succesfully\n";	
		exit 0;
	}

    if ($opt eq 'cleancookies'){
        print "This will clean the entire cookie directory at $cookiesdir.\n";
        print "Proceed ? [y/n]";
        $ynchoice = <STDIN>;
        chomp $ynchoice;
        if ($ynchoice eq 'o' or $ynchoice eq 'y'){
            rmtree("$cookiesdir",{safe=>1,keep_root=>1});
            print "All cookies have been cleaned. Tell your users to clear their caches and reconnect.\n";
        }
        exit 0;
    }

    if ($opt eq 'cleanlinks'){
        $ynchoice = <STDIN>;
        chomp $ynchoice;
        if ($ynchoice eq 'o' or $ynchoice eq 'y'){
            rmtree("$web_dir/cgi-bin/l",{safe=>1,keep_root=>1});
            print "All generated links have been deleted.\n";
        }
        exit 0;
    }
    
    if ($opt eq 'invite'){
        my $verb = shift;
        if ($verb eq 'gen'){
            my $preconf_mail = undef;
            my $mailfield = q{<input type="text" name="mailaddr" required>};
            my $for_x = undef;
            print "Set an email address beforehand ? [y/n] ";
            $ynchoice = <STDIN>;
            chomp $ynchoice;
            if ($ynchoice eq 'o' or $ynchoice eq 'y'){
                $preconf_mail = SetMail();
                $mailfield = qq{<input value="$preconf_mail" type="text" name="mailaddr" required disabled>};
                $for_x = "for $preconf_mail";
            }
            use File::Path qw/mkpath/;
            mkpath($invites_dir) unless -d $invites_dir;
            my $randengine = String::Random->new;
            my $randfn = $randengine->randregex('\w{64}') . '.cgi';
            my $invite_path = "$invites_dir/$randfn";
            open my $in, '<', $invites_tmpl or die "Can't open template for invites : $!";
            open my $out, '>', $invite_path or die "Can't write to invite path: $!";
            while (<$in>) {
                s/{mailfield_goes_here}/{$mailfield}/g;
                print $out $_;
            }
            close $in or die "$!";
            chmod(0755, $invite_path) or die "$!";
            close $out or die "$!";
            print "\nSuccess ! The link was generated to $invite_path $for_x.";
        }

    }

    if ($opt eq 'version'){
        print "$version\n";
        exit 0;
    }

    if ($opt eq 'list'){
        my $verb = shift;
        if (defined $verb){
            if ($verb eq 'users'){
                my $dbh = DBI->connect("DBI:SQLite:dbname=$dbh_path", undef, undef,
                {
                    RaiseError => 1,
                    AutoCommit => 1,
                }) or die $DBI::errstr;
                ListUsers($dbh);
            }
        }
        else{
            print "Valid 'list' actions are:\n\tusers\n" ;
        }
    }

    PrintHelp();
}
else {
    PrintHelp();
}
