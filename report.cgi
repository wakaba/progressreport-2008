#!/usr/bin/perl
use strict;
use CGI::Carp qw(fatalsToBrowser);

my $path = $ENV{PATH_INFO};

my $users_sorted = [
  'XXXuser1',
  'XXXuser2',
];

my $users = {};
$users->{$_} = 1 for @$users_sorted;

require Encode;
my $user_names = {
  'XXXuser1' => char ('XXX User 1'),
  'XXXuser2' => char ('XXX User 2'),
};

my $data_dir_name = q[data/];

sub htescape ($) {
  my $s = shift;
  $s =~ s/&/&amp;/g;
  $s =~ s/</&lt;/g;
  $s =~ s/>/&gt;/g;
  $s =~ s/"/&quot;/g;
  $s =~ s/([^\x00-\x7f])/sprintf '&#x%04X;', ord $1/ge;
  return $s;
} # htescape

sub get_date_text (%) {
  my %in = @_;
  if ($in{yyyy_mm_dd}) {
    return sprintf '%04d-%02d-%02d', @{$in{yyyy_mm_dd}};
  } elsif ($in{yyyymmdd}) {
    if ($in{yyyymmdd} =~ /^([0-9]{4})([0-9]{2})([0-9]{2})$/) {
      return qq[$1-$2-$3];
    } else {
      return qq[????-??-??];
    }
  } elsif ($in{unixtime}) {
    my @time = gmtime $in{unixtime};
    return sprintf qq[%04d-%02d-%02d],
        $time[5] + 1900, $time[4] + 1, $time[3];
  } else {
    die "$0: get_date_text: broken";
  }
} # get_date_text

sub get_users_box ($;$) {
  my $field_name = shift;
  my $default = shift || '';
  my $has_default;
  my $r = qq[<select name="@{[htescape ($field_name)]}" id="@{[htescape ($field_name)]}">];
  for (@$users_sorted) {
    $r .= q[<option];
    $r .= q[ selected] and $has_default = 1 if $default eq $_;
    $r .= q[>] . htescape ($_);
  }
  $r .= q[<option value="" disabled];
  $r .= q[ selected] unless $has_default;
  $r .= q[>Name...];
  $r .= q[</select>];
  return $r;
} # get_users_box

sub u8 ($) {
  return Encode::encode ('utf-8', $_[0]);
} # u8

sub char ($) {
  return Encode::decode ('euc-jp', $_[0]);
} # char

if ($path eq '/list') {
  my $dates = {};
  my $has_file = {};
  {
    opendir my $data_dir, $data_dir_name or die "$0: $data_dir_name: $!";
    for (readdir $data_dir) {
      if (/^([a-z-]+)_([0-9]{8})\.dat$/) {
        push @$users_sorted, $1 unless $users->{$1};
	$users->{$1} = 1;
	$dates->{$2} = 1;
	$has_file->{$1}->{$2} = 1;
      }
    }
  }
  
  print qq[Content-Type: text/html; charset=utf-8

<!DOCTYPE HTML>
<html lang=en>
<title>List of reports</title>
<h1>List of reports</h1>
<nav>[<a href=submit>submit</a>]</nav>
<table>
<thead>
<tr><th>Date
];
  for (@$users_sorted) {
    print qq[<th>], htescape ($_);
  }
  print qq[<th>SPB Report<tbody>];

  for my $date (sort {$b <=> $a} keys %$dates) {
    print qq[<tr><th><time>], get_date_text (yyyymmdd => $date), q[</time>];
    for my $user (@$users_sorted) {
      if ($has_file->{$user}->{$date}) {
        my $uri = qq[entry/$user/$date];
	print qq[<td class=has-file><a href="], htescape ($uri);
        print q[">submitted</a>];
      } else {
	print qq[<td class=no-file>];
      }
    }
    print qq[<td><a href="spb/$date">create</a>];
  }
  exit;
} elsif ($path =~ m[^/entry/([a-z-]+)/([0-9]{8})$]) {
  my $file_name = $data_dir_name . $1 . '_' . $2 . '.dat';
  if (-f $file_name) {
    open my $file, '<:utf8', $file_name or die "$0: $file_name: $!";
    local $/ = undef;
    no strict;
    my $data = eval scalar <$file>;
    print scalar get_submission_form ($data, '../../');
    exit;
  } else {
    # (404)
  }
} elsif ($path =~ m[^/spb/([0-9]{8})$]) {
  my $date = $1;
  my $r = '';
  for my $user (@$users_sorted) {
    my $file_name = $data_dir_name . $user . '_' . $date . '.dat';
    if (-f $file_name) {
      open my $file, '<:utf8', $file_name or die "$0: $file_name: $!";
      local $/ = undef;
      no strict;
      my $data = eval scalar <$file>;
      if (length $data->{'spb-report'}) {
	$r .= '* ' . $user_names->{$user} . "\n\n";
	$r .= $data->{'spb-report'};
	$r .= "\n\n";
      }
    }
  }

  print qq[Content-Type: text/html; charset=utf-8

<!DOCTYPE HTML>
<html lang=en>
<title>SPB Report</title>
<style>
textarea {
  width: 90%;
  height: 20em;
}
</style>
<h1>SPB Report</h1>

<textarea lang="">@{[htescape ($r)]}</textarea>];

  exit;
} elsif ($path eq '/submit') {
  my $method = $ENV{REQUEST_METHOD};
  if ($method eq 'POST') {
    eval qq{ use CGI qw/param/ };

    my $data = {};

    my $name = param ('name');
    unless ($users->{$name}) {
      print qq[Status: 400 Bad Name
Content-Type: text/plain; charset=us-ascii

Not a valid user name];
      exit;
    }
    $data->{name} = $name; # redundant with file name

    my $date = param ('date');
    my ($y, $m, $d);
    if ($date =~ /^([0-9]{4})-([0-9]{1,2})-([0-9]{1,2})$/) {
      ($y, $m, $d) = ($1+0, $2+0, $3+0);
    } else {
      print qq[Status: 400 Bad date
Content-Type: text/plain; charset=us-ascii

Not a valid date (YYYY-MM-DD format)];
      exit;
    }
    $data->{date} = [$y, $m, $d]; # redundant with file name
    
    require Encode;
    for my $item (qw/progress questions todos spb-report/) {
      my $v = param ($item);
      if (defined $v) {
	$data->{$item} = Encode::decode ('utf-8', $v);
      }
    }

    my $file_name = $data->{name} . '_';
    $file_name .= sprintf '%04d%02d%02d.dat', $y, $m, $d;
    {
      eval qq{ use Data::Dumper };
      open my $file, '>:utf8', $data_dir_name . $file_name
	  or die "$0: $data_dir_name$file_name: $!";
      print $file Dumper ($data);
      close $file;
      my $result = `cd $data_dir_name && svn add $file_name && svn commit -m "Auto"`;
      unless ($result =~ /Committed/) {
	print qq[Status: 500 SVN Commit Error
Content-Type: text/plain;  Charset=iso-8859-1

SVN Commit Error:

$result];
	exit;
      }
    }

    print qq[Status: 201 Created
Content-Type: text/html; charset=us-ascii

<meta http-equiv=Refresh content="0; url=list">
<h1>Submitted</h1>
<nav>[<a href=list>list</a>]</nav>];
    
    exit;
  } else {
    print scalar get_submission_form ({todos => char (q[- 短期的な予定 (次の SPB まで)

- 中期的な予定

- 長期的な予定

])}, './');
    exit;
  }
}

sub get_submission_form ($$) {
  my $data = shift;
  my $base_uri = shift;
  return u8 (char (qq[Content-Type: text/html; charset=utf-8

<!DOCTYPE HTML>
<title>報告の提出</title>
<style>
table {
 width: 90%;
}
th {
  text-align: left;
}
th:after {
  content: ": ";
}
textarea {
  width: 90%;
  height: 15em;
}
input {
  min-width: 10em;
}
</style>
<h1>報告の提出</h1>

<form action="${base_uri}submit" method=post accept-charset=utf-8>
<input name=_charset_ type=hidden>
<table>
<tr><th><label for=name>名前</label>
    <td>@{[get_users_box ('name', $data->{name})]}
<tr><th><label for=date>日付</label>
    <td><input type=date name=date id=date value="@{[htescape (get_date_text (yyyy_mm_dd => $data->{date}, unixtime => scalar time))]}">
<tr><th colspan=2><label for=progress>これまでの作業内容</label>
<tr><td colspan=2><textarea name=progress id=progress>@{[htescape ($data->{progress})]}</textarea>
<tr><th colspan=2><label for=questions>質問、困っている点</label>
<tr><td colspan=2><textarea name=questions id=questions>@{[htescape ($data->{questions})]}</textarea>
<tr><th colspan=2><label for=todos>今後の作業予定</label>
<tr><td colspan=2><textarea name=todos id=todos>@{[htescape ($data->{todos})]}</textarea>
<tr><th colspan=2><label for=spb-report>SPB のまとめ</label>
<tr><td colspan=2><textarea name=spb-report id=spb-report>@{[htescape ($data->{'spb-report'})]}</textarea>
<tfoot>
<tr><td colspan=2><button>提出</button>
</table>
</form>]));
} # get_submission_from

print q[Content-Type: text/plain; charset=us-ascii
Status: 404 Not Found

404];

