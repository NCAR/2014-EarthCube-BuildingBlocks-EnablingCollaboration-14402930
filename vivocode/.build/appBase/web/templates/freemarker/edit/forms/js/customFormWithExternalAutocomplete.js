/* $This file is distributed under the terms of the license in /doc/license.txt$ */

//Determine which javascript will be used based on serviceURI


function getCustomFormHandler(serviceURI) {
	//Maps a serviceURI to an actual variable, i.e. the custom lookup handler object
	var mapping = {"externalSolr":getExternalLookup_solr};
	if((serviceURI == null) || (!(serviceURI in mapping))) {
		return customForm;
	}
	return mapping[serviceURI];
}



$(document).ready(function() {
	var serviceURI = customFormData.serviceURI;
	var customFormHandler = getCustomFormHandler(serviceURI);
	//Retrieve appropriate custom form lookup JavaScript based on serviceURI
	if(customFormHandler && $.isFunction(customFormHandler.getLookup)) {
		
		var customForm = customFormHandler.getLookup();
		customForm.onLoad();
	} 
});
