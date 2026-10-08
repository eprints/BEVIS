=head1 NAME

EPrints::Plugin::Screen::ClearNginxCache

Button to clear the nginx cache

=cut


package EPrints::Plugin::Screen::Admin::ClearNginxCache;

use EPrints::Plugin::Screen;
use File::Path;

@ISA = ( 'EPrints::Plugin::Screen' );

use strict;

sub new
{
	my( $class, %params ) = @_;

	my $self = $class->SUPER::new(%params);
	
	$self->{actions} = [qw/ clear_nginx_cache /];

	$self->{appears} = [
		{ 
			place => "admin_actions_system",
			action => "clear_nginx_cache",
			position => 126, 
		}
	];
	return $self;
}

sub allow_clear_nginx_cache
{
	my( $self ) = @_;
	return $self->allow( "config/regen_abstracts" );
}

sub about_to_render
{
	my( $self ) = @_;
	$self->{processor}->{screenid} = "Admin";
}

sub action_clear_nginx_cache
{
	my( $self ) = @_;

	EPrints::Utils::rmtree('/opt/eprints3/var/cache/nginx/everything_else_cache');
	EPrints::Utils::rmtree('/opt/eprints3/var/cache/nginx/cpu_heavy_cache');

	# alternative mechanism is to configure the special purge request and send that

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

