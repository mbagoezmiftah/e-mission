'use strict';

/*
 *  Set site-level variables (required)
 */
 $(document).ready( function(){

    window.nrel = $.extend({}, window.nrel); // Merge in page level variables if they are set
    window.nrel.pagevars = $.extend({}, window.nrel.pagevars); // (in case window.nrel isn't defined)

    window.nrel.pagevars.sitename = 'AppName';

    var $navlink,
        $navitem,
        slash,
        nrel,
        pv;

    // shorthand alias for our page variables
    nrel = window.nrel || {};
    pv = nrel.pagevars || {};


    pv.pagename = $('h1').text();
    slash = location.pathname.lastIndexOf('/') + 1;

    pv.pageurl  = location.pathname;                 //  /foo/bar/baz/boink.html
    pv.siteurl  = location.pathname.substr(0,slash); //  /foo/bar/baz/
    pv.filename = location.pathname.substr(slash) ;  //  boink.html

    // catch situations where the url ends in a slash, with index.html implied
    if( ! pv.filename.length) {
        pv.filename = 'index.html'; // this could be index.php or index.cfm, or ...
    }


    /*
     * Contact Us footer link
     * if the site doesn't defer to the globalwebmaster, use the local one
     */
    if( !pv.globalwebmaster && pv.sitename ) {
        $('#contact-link').attr( 'href', pv.siteurl + 'contacts.html' );
    } else {
        $('#contact-link').attr( 'href', '/webmaster.html' );
    }
	
	});

	 /*
     * Custom Threads button for ShareThis
     */
	function updateThreadsLink() {
		const currentUrl = window.location.href;
		const currentTitle = document.title;
		const encodedTitle = encodeURIComponent(currentTitle);
		const encodedUrl = encodeURIComponent(currentUrl);
		const updatedUrl = `https://www.threads.net/intent/post?text=${encodedTitle}%0A${encodedUrl}`;

		// Calculate the position to center the window
		const screenWidth = window.screen.width;
		const screenHeight = window.screen.height;
		const windowWidth = 785;
		const windowHeight = 450;
		const left = (screenWidth - windowWidth) / 2;
		const top = (screenHeight - windowHeight) / 2;

		// Open the link in a new window with specific size and position
		const windowFeatures = `width=${windowWidth},height=${windowHeight},left=${left},top=${top}`;
		window.open(updatedUrl, 'myWindow', windowFeatures);
	}
	document.getElementById("thispage").addEventListener("click", updateThreadsLink);