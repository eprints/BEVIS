# If EPrints supports it, disable the cache tables so we can make better use of nginx's cache 
# cache tables are overwhelmed by the sheer quantity of searches now, so aren't useful anymore anyway
$c->{search_uses_cache_tables} = 0;