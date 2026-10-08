=head1 NAME

EPrints::Plugin::Screen::AnubisStatus

Simple page to report back the otherwise hard to access metrics page from anubis.
This isn't super useful as it reports only current accumulated statistics. Ideally we'd need to track this over time
and graph it to get an idea of spikes of bot activity.

=cut


package EPrints::Plugin::Screen::Admin::AnubisStatus;

use EPrints::Plugin::Screen;
use File::Temp qw/ tempfile tempdir /;

@ISA = ( 'EPrints::Plugin::Screen' );

use strict;

sub new
{
	my( $class, %params ) = @_;

	my $self = $class->SUPER::new(%params);
	
	$self->{appears} = [
		{
			place => "admin_actions_system",
			position => 125,
		},
	];
	return $self;
}

sub can_be_viewed
{
	my( $self ) = @_;

    # if you can view the event queue, why not view anubis status?
	return $self->allow( "event_queue/view" );
}

sub render
{
	my( $self ) = @_;

	my $session = $self->{session};
	my $user = $session->current_user;

	my $rows;

    my ($tmpfile, $tmpfile_name) = tempfile();
    
    my $ua = LWP::UserAgent->new();

    my $repo = $session->get_repository;

    my $url = $repo->config( 'anubis', 'metrics_url' );

	my $r = $ua->get( $url,
		":content_file" => $tmpfile_name
	);

    my( $html , $table , $p , $span );
    
    my $fetch_success = 0;
    if( $r->is_success )
    {   
        seek( $tmpfile, 0, 0 );
        $fetch_success = 1;
    }
    else
    {
        $session->get_repository->log( "Failed to retrieve anubis metrics: " . $r->code . " " . $r->message );
    }

    my @lines = <$tmpfile>;

	
	 $repo->config( 'matomo', 'idsite' ),
	# Write the results to a table
	
	$html = $session->make_doc_fragment;

    my $title = $session->make_element( "h2" );
    $title->appendChild( $session->make_text( "Anubis Metrics" ) );

    if(!$fetch_success){
        $html->appendChild($session->make_text( "Failed to retrieve ". $url ." : " . $r->code . " " . $r->message));
    }

    $html->appendChild($title);

	$table = $session->make_element( "table", class=>"ep_table ep_no_border" );
	$html->appendChild( $table );
	
    for my $line ( @lines ){
        my $firstCharacter = substr $line, 0, 1;

        if( $firstCharacter ne "#"){

            my @parts = split ' ', $line;
            $table->appendChild( 
                $session->render_row( 
                    $session->make_text( $parts[0] ),
                    $session->make_text( $parts[1] ) 
                    ) 
                );
        }
    }

	

	return $html;
}




1;

=head1 COPYRIGHT

=for COPYRIGHT BEGIN

Copyright 2022 University of Southampton.
EPrints 3.4 is supplied by EPrints Services.

http://www.eprints.org/eprints-3.4/

=for COPYRIGHT END

=for LICENSE BEGIN

This file is part of EPrints 3.4 L<http://www.eprints.org/>.

EPrints 3.4 and this file are released under the terms of the
GNU Lesser General Public License version 3 as published by
the Free Software Foundation unless otherwise stated.

EPrints 3.4 is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with EPrints 3.4.
If not, see L<http://www.gnu.org/licenses/>.

=for LICENSE END

