/* $This file is distributed under the terms of the license in /doc/license.txt$ */

$(document).ready(function(){
    //Shortcut, usually utilize an object
	getExternalInfo();
	function getExternalInfo() {
		
		 $.each($('ul.external-property-list'), function() {
			 var externalServiceURL = $(this).attr("externalServiceURL");
			 var externalURI = $(this).attr("externalURI");
			 var propertyURI = $(this).attr("propertyURI");
			 var domainURI = $(this).attr("domainURI");
			 var rangeURI = $(this).attr("rangeURI");
			 var externalBaseURL = $(this).attr("externalBaseURL");
			 //These should be empty strings and not null/undefined when values don't exist
			 if(externalServiceURL != null && externalServiceURL != "") {
				 //Call ajax to get the content
				 var data = {"serviceURL": externalServiceURL, 
						 "propertyURI": propertyURI, 
						 "domainURI":domainURI, 
						 "rangeURI":rangeURI};
				 var externalIndController = "http://localhost:8080/earthcollabvivo/externalIndividualController";
				 
					 $.getJSON(externalIndController, data, function(results) {
					 parseExternalContent(results, externalURI, externalBaseURL);
					 });
				
			 }
		 });
		
		
		
	}
	
	//Hardcoding retrieval of publications but this should be based on
	//the property, domain, and range info being set on the datagetter and set as attributes
	//on the element
	function parseExternalContent(results, externalURI, externalBaseURL) {
		//TODO: Figure out a way to execute the Freemarker template? From within JAVA?
		var displayHTML = "";
		if("subclasses" in results) {
			//subclasses within results
			var subclassesArray = results.subclasses;
			if(subclassesArray.length > 0) {
				for(s = 0; s < subclassesArray.length; s++) {
					var subclass = subclassesArray[s];
					var name = subclass.name;
					var statements = subclass.statements;
					if(statements.length > 0) {
						//Copying how regular items are displayed but this may have consequences for 
						displayHTML += "<li class='subclass' role='listitem'>" + name + "<ul class='subclass-property-list'>";
						var i;
						for(i = 0; i < statements.length; i++) {
							var statement = statements[i];
							if("allData" in statement) {
								var statementData = statement.allData;
								//For publisher, hard coding right now
								var pubName = statementData.infoResourceName;
								var infoResourceURI = statementData.infoResource;
								var externalPubURL = externalBaseURL + "/individual?uri=" + infoResourceURI;
								displayHTML += "<li role='listitem'><a title='resource name' href='" + externalPubURL + "'>" + pubName + "</a></li>";
							}
						}
						displayHTML += "</ul></li>";
					}
				}
			}
		}
		$("ul[externalURI='" + externalURI + "']").append("<li>" + displayHTML + "</li>");
	}
 
});


