/* $This file is distributed under the terms of the license in /doc/license.txt$ */
/** This file represents specific javascript for autocomplete for postgres**/

/*
function Solr_handler() {}
Solr_handler.prototype = customForm;

//Based on the raw label and the rest of the data
Solr_handler.prototype.updateLabelForDisplay=function(result) {
	var label = result.label +  " SOLR(" + result.typeString + ")";
	//update label
	result["label"]= label;
}
//Pass in all of the data, i.e. array of results
Solr_handler.prototype.updateLabelsForDisplay=function(results) {
	var len = results.length;
	var i;
	for(i = 0; i < len; i++) {
		Solr_handler.prototype.updateLabelForDisplay(results[i]);
	}
}

//Do we override methods here?
var externalLookup_solr = new Solr_handler();
*/


var Solr_handler = {
		//Based on the raw label and the rest of the data
		updateLabelForDisplay:function(result) {
			//If typestring is undefined or null, don't add
			var typeInfo = "";
			if("typeString" in result && result.typeString != undefined) {
				typeInfo = " (" + result.typeString + ")";
			}
			var label = result.label +  typeInfo;
			//update label
			result["label"]= label;
		},
		//Pass in all of the data, i.e. array of results
		updateLabelsForDisplay:function(results) {
			var len = results.length;
			var i;
			for(i = 0; i < len; i++) {
				Solr_handler.updateLabelForDisplay(results[i]);
			}
		}
};


//Do we override methods here?
var getExternalLookup_solr= {
	getLookup:function() {
		return inherit(customForm, Solr_handler);
	}
}


