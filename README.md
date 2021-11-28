# Wikipedia-to-wordpress
A small python program to transform a Wikipedia page into a Wordpress post
The script takes a Wikipedia page using the Wikipedia page API. Typical usage relies on the command line:

  python3 wikipedia_to_wordpress.py "Diamond open access"

Most of the transformations are trivial and aim at simplifying the wikipedia HTML code.

The only tricky part are the references: the complicated Wikipedia reference system (with harvsp) is replaced by a tooltip, using the tooltip shortcode from the Shortcodes Ultimate extension.
