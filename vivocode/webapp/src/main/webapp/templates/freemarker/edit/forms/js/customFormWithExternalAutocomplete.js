/* $This file is distributed under the terms of the license in /doc/license.txt$ */

//Determine which javascript will be used based on serviceURI


function getCustomFormHandler(serviceURI) {
	//this code is initialized when the page loads - but we don't want handling to occur until the user actually selects an input and begins to type?
	//or at least selects an input
	//Maps a serviceURI to an actual variable, i.e. the custom lookup handler object
	var mapping = {"http://vivo.earthcollab.edu/individual/climateSolrLookup":getExternalLookup_solr,
			"http://vivo.earthcollab.edu/individual/cornellSolrLookup":getExternalLookup_solr,
			"http://vivo.earthcollab.edu/individual/testCornellSolrLookup":getExternalLookup_solr};
	
	if((serviceURI == null) || (!(serviceURI in mapping))) {
		return customForm;
	}
	return mapping[serviceURI];
}

function selectCustomFormHandler(serviceURI) {
	var customFormHandler = getCustomFormHandler(serviceURI);
	//Retrieve appropriate custom form lookup JavaScript based on serviceURI
	if(customFormHandler && $.isFunction(customFormHandler.getLookup)) {
		//Not sure if this will work with same code and different lookup?
		var customForm = customFormHandler.getLookup();
		//set the serviceURI
		customForm["serviceURI"] = serviceURI;
		customForm.onLoad();
	} 
}

$(document).ready(function() {
	//some default value
	var serviceURI =$("input[name='serviceURI']:checked").val();
	selectCustomFormHandler(serviceURI);
	$("input[name='serviceURI']").change(function() {
		//Select a different custom form handler if required
		serviceURI = $(this).val();
		selectCustomFormHandler(serviceURI);
		//this problematic given the other events that could be bound?
		//will have to try this out and see
	})
	
});
