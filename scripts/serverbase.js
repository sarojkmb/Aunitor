(function ($) {
	
	$(window).on('scroll', function () {
		if ($(this).scrollTop() >= 100) {
			$('div.header').addClass('fix-header');
		} else {
			$('div.header').removeClass('fix-header');
		}
	});
	
	$('div.search-section input').on('focus', function () {
		$(this).closest('div.search-section').addClass('search-focus');
	});
	$('div.search-section input').on('blur', function () {
		$(this).closest('div.search-section').removeClass('search-focus');
	});
	
	$('div.search-section input').focus();

	
	
	$('a#atab-myserver').on('click', function () {
		$('div.clswitchtabs>ul.lsttabs>li>a').removeClass('tabselected');
		$(this).addClass('tabselected');
		$('div.tab-content').hide();
		$('div#tabcontent-myserver').show();
	});
	$('a#atab-allserver').on('click', function () {
		$('div.clswitchtabs>ul.lsttabs>li>a').removeClass('tabselected');
		$(this).addClass('tabselected');
		$('div.tab-content').hide();
		$('div#tabcontent-allserver').show();
	});
	$('a#atab-adminserver').on('click', function () {
		$('div.clswitchtabs>ul.lsttabs>li>a').removeClass('tabselected');
		$(this).addClass('tabselected');
		$('div.tab-content').hide();
		$('div#tabcontent-adminserver').show();
	});
	
	$('ul.lst-create-group>li>a.group-item').on('click', function () {
	  $(this).toggleClass('group-selected');
	});
	
})(jQuery);