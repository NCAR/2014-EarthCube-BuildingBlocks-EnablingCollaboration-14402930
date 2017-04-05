/* $This file is distributed under the terms of the license in /doc/license.txt$ */

$(document).ready(function(){
    //Shortcut, usually utilize an object
	getExternalInfo();
	function getExternalInfo() {
		var externalURIHash = createExternalURIHash();
		for(var key in externalURIHash) {
			//Each key represents a unique endpoint request, i.e. external URI + external Service URL
			var externalInfo = externalURIHash[key];
			var externalServiceURL = externalInfo["externalServiceURL"];
			var externalURI =  externalInfo["externalURI"];
			 
			var externalBaseURL =  externalInfo["externalBaseURL"];
			var externalSourceLabel =  externalInfo["sourceLabel"];
			 
			//Include icons for linked images on page
			displayExternalLinkedIcons(externalURI, externalBaseURL, externalSourceLabel);
			
			var propertyList = externalInfo["properties"];
			var plen = propertyList.length;
			var p;
			var data = {
				"serviceURL": externalServiceURL, 
				"properties": JSON.stringify(propertyList),
				"propertiesLength": propertyList.length
				};
						 
			var externalIndController = appBase + "/externalIndividualController";
						 
			$.getJSON(externalIndController, data, function(allResults) {
				if(allResults != null && allResults != "") {
					for(propertyKey in allResults) {
						var propertyInfo = allResults[propertyKey];
						//Requesting a property doesn't entail information being available
						if(propertyInfo && propertyInfo != null) {
							parseExternalContent(propertyInfo, externalURI, externalBaseURL, externalSourceLabel, propertyInfo["uri"], propertyInfo["domainUri"], propertyInfo["rangeUri"]);
						} else {
							//if information is not being returned, then go ahead and replace the external content div
								var propertyInfoItems = propertyKey.split("-");
								console.log(propertyInfoItems);
								if(propertyInfoItems.length == 3) {
									var propertyURI = propertyInfoItems[0];
									var domainURI = propertyInfoItems[1];
									var rangeURI = propertyInfoItems[2];
									var contentItem = getExternalContentItem(externalURI, propertyURI, domainURI, rangeURI);
									contentItem.replaceWith("");
									hideLoadingIndicator(externalURI, propertyURI, domainURI, rangeURI);
								}
							
						}
					}
				}
				//parseExternalContent(results, externalURI, externalBaseURL, externalSourceLabel, propertyURI, domainURI, rangeURI);
			});
			
		 }
			 
		}
	
		function displayExternalLinkedIcons(externalURI, externalBaseURL, externalSourceLabel) {
			if(externalURI != "" && externalBaseURL != "") {
				var imageHTML = "<a  href='" + externalBaseURL + "/individual?uri=" + externalURI + "' title='see linked profile at " + externalSourceLabel + "'><img class='linkedprofile' src='" + baseUrl + "/images/cornellvivoicon2.png'></a>";
				$("#externalProfileImages").append(imageHTML);
			}
		}
//		 $.each($('li.external-property-list-item'), function() {
//			 var externalServiceURL = $(this).attr("externalServiceURL");
//			 var externalURI = $(this).attr("externalURI");
//			 var propertyURI = $(this).attr("propertyURI");
//			 var domainURI = $(this).attr("domainURI");
//			 var rangeURI = $(this).attr("rangeURI");
//			 var externalBaseURL = $(this).attr("externalBaseURL");
//			 var externalSourceLabel = $(this).attr("sourceLabel");
//			 //These should be empty strings and not null/undefined when values don't exist
//			 if(externalServiceURL != null && externalServiceURL != "") {
//				 //Call ajax to get the content
//				 var data = {"serviceURL": externalServiceURL, 
//						 "propertyURI": propertyURI, 
//						 "domainURI":domainURI, 
//						 "rangeURI":rangeURI};
//				 //appBase is variable defined in individual-property-group-tabs
//				 var externalIndController = appBase + "/externalIndividualController";
//				 
//					 $.getJSON(externalIndController, data, function(results) {
//					 parseExternalContent(results, externalURI, externalBaseURL, externalSourceLabel, propertyURI, domainURI, rangeURI);
//					 });
//				
//			 }
//		 });
		
		
		

	
	//Create a hash of information based on what external uris are indiciated within the page
	function createExternalURIHash() {
		var externalURIHash = {};
		$.each($('li.external-property-list-item'), function() {
			 var externalServiceURL = $(this).attr("externalServiceURL");
			 var externalURI = $(this).attr("externalURI");
			 var propertyURI = $(this).attr("propertyURI");
			 var domainURI = $(this).attr("domainURI");
			 var rangeURI = $(this).attr("rangeURI");
			 var externalBaseURL = $(this).attr("externalBaseURL");
			 var externalSourceLabel = $(this).attr("sourceLabel");
			 //These should be empty strings and not null/undefined when values don't exist
			 if(externalURI != null && externalURI != "" && externalServiceURL != null && externalServiceURL != "") {
				 
				 var key = externalURI + "-" + externalServiceURL;
				 var propertiesList = [];
				 if(! (key in externalURIHash)) {
					 externalURIHash[key] = {
							 "externalURI": externalURI,
							 "externalServiceURL": externalServiceURL,
							 "externalBaseURL": externalBaseURL,
							 "sourceLabel": externalSourceLabel,
							 "properties": []
					 };
				 }
				 
				 var einfo = externalURIHash[key];
				 propertiesList = einfo["properties"];
				 propertiesList.push({
					 "propertyURI": propertyURI,
					 "domainURI": domainURI,
					 "rangeURI": rangeURI
				 });
				 //einfo["properties"] = propertiesList;
				// externalURIHash[key] = einfo;
			 }
		});
		return externalURIHash;
	}
	
	//Hardcoding retrieval of publications but this should be based on
	//the property, domain, and range info being set on the datagetter and set as attributes
	//on the element
	function parseExternalContent(results, externalURI, externalBaseURL, externalSourceLabel, propertyURI, domainURI, rangeURI) {
		//TODO: Figure out a way to execute the Freemarker template? From within JAVA?
		var displayHTML = "";
		//Need to also handle case where there are no subclasses
		if("subclasses" in results) {
			//subclasses within results
			var subclassesArray = results.subclasses;
			if(subclassesArray.length > 0) {
				for(s = 0; s < subclassesArray.length; s++) {
					var subclass = subclassesArray[s];
					
					var statements = subclass.statements;
					displayHTML += createDisplayHTML(statements, subclass, null, propertyURI, domainURI, rangeURI, externalURI, externalBaseURL, externalSourceLabel);
				}
			}
		} else {
			if("statements" in results && results["statements"].length > 0 ) {
					var statements = results["statements"];
					var displayName = results["name"].toLowerCase();
					var displayHTML = createDisplayHTML(statements, null, displayName, propertyURI, domainURI, rangeURI, externalURI, externalBaseURL, externalSourceLabel);
							
			}
		}
		//$("ul[externalURI='" + externalURI + "']").append("<li>" + displayHTML + "</li>");
		//If SOMETHING to display, should display otherwise this should be removed
		var contentItem = getExternalContentItem(externalURI, propertyURI, domainURI, rangeURI);
		showContentItem(displayHTML, contentItem);
		hideLoadingIndicator(externalURI, propertyURI, domainURI, rangeURI);
	}
	
	function getExternalContentItem(externalURI, propertyURI, domainURI, rangeURI) {
		return $("li.external-property-list-item[externalURI='" + externalURI + "'][propertyURI='" + propertyURI + "'][domainURI='" + domainURI + "'][rangeURI='" + rangeURI + "']");
	}
	
	function showContentItem(displayHTML, contentItem) {
		contentItem.replaceWith(displayHTML);
		contentItem.removeClass("hidden");
	}
	
	function hideLoadingIndicator(externalURI, propertyURI, domainURI, rangeURI) {
		var indicator = $("li.li-indicator[externalURI='" + externalURI + "'][propertyURI='" + propertyURI + "'][domainURI='" + domainURI + "'][rangeURI='" + rangeURI + "']");
		indicator.addClass("hidden");
	}
	
	function createDisplayHTML(statements, subclass, displayName, propertyURI, domainURI, rangeURI, externalURI, externalBaseURL, externalSourceLabel) {
		//["http://vivoweb.org/ontology/core#relatedBy-http://xmlns.com/foaf/0.1/Person-http://vivoweb.org/ontology/core#Position"]

		if(propertyURI == "http://vivoweb.org/ontology/core#relatedBy" && domainURI == "http://xmlns.com/foaf/0.1/Person" && rangeURI == "http://vivoweb.org/ontology/core#Position") {
			return createPositionsHTML(statements, displayName, externalURI, externalBaseURL, externalSourceLabel);
		} else if(propertyURI == "http://vivoweb.org/ontology/core#relatedBy" && domainURI == "http://xmlns.com/foaf/0.1/Person" && rangeURI == "http://vivoweb.org/ontology/core#Authorship") {
			return createPublicationsHTML(statements, subclass,externalURI, externalBaseURL, externalSourceLabel);
		} else if(propertyURI == "http://purl.obolibrary.org/obo/ARG_2000028" && domainURI == "http://xmlns.com/foaf/0.1/Person" && rangeURI == "http://www.w3.org/2006/vcard/ns#Work") {
			return createEmailHTML(statements, subclass,externalURI, externalBaseURL, externalSourceLabel);
		}
		else if(propertyURI == "http://purl.obolibrary.org/obo/ARG_2000028" && domainURI == "http://xmlns.com/foaf/0.1/Person" && rangeURI == "http://www.w3.org/2006/vcard/ns#Email") {
			return createEmailHTML(statements, subclass,externalURI, externalBaseURL, externalSourceLabel);
		}
	}
	
	function createPublicationsHTML(statements, subclass, externalURI, externalBaseURL, externalSourceLabel) {
		var name = subclass.name;
		var displayHTML = "";
		if(statements.length > 0) {
			var subclassDisplayName = name.toLowerCase();
			if(externalSourceLabel) {
				subclassDisplayName += externalSourceLabel ;
			}
			displayHTML += "<li class='subclass' role='listitem'><h3>" + subclassDisplayName + "</h3><ul class='subclass-property-list'>";
			
			var i;
			for(i = 0; i < statements.length; i++) {
				var statement = statements[i];
				if("allData" in statement) {
					var statementData = statement.allData;
					//For publisher, hard coding right now
					var pubName = statementData.infoResourceName;
					var infoResourceURI = statementData.infoResource;
					var externalPubURL = externalBaseURL + "/individual?uri=" + infoResourceURI;
					displayHTML += "<li role='listitem'><a title='resource name' href='" + externalPubURL + "'>" + pubName + "</a>";
					//if(externalSourceLabel) {
					//	displayHTML += "<br/>" + externalSourceLabel ;
					//}
					displayHTML += "</li>";

				}
			}
			displayHTML += "</ul></li>";
		}
		return displayHTML;
		
	}
	
	function createPositionsHTML(statements, displayName, externalURI, externalBaseURL, externalSourceLabel) {
		var displayHTML = "";
		var i;
		for(i = 0; i < statements.length; i++) {
			var statement = statements[i];
			if("allData" in statement) {
				var statementData = statement.allData;
				
				//if position
				if(displayName == "positions") {
					dataExists = true;
					var positionTitle = statementData["positionTitle"];
					displayHTML += "<li role='listitem'>" + positionTitle;
					if("orgName" in statementData) {
						displayHTML += ", " + statementData["orgName"];
					}
					if ("middleOrgName" in statementData) {
						displayHTML += ", " + statementData["middleOrgName"];
					}
					
					if ("outerOrgName" in statementData) {
						displayHTML += ", " + statementData["outerOrgName"];
					}
					
				}
				//org, outerOrg, position, middleOrg are all URLs so those can be included if need be
				displayHTML += "<span style='font-size:0.825em'>* " + externalSourceLabel + "</span></li>";
			}
		}
		return displayHTML;
		
	}
	
	function createEmailHTML(statements, subclass,externalURI, externalBaseURL, externalSourceLabel) {
		var displayHTML = "";
		var i;
		for(i = 0; i < statements.length; i++) {
			var statement = statements[i];
			if("allData" in statement) {
				var statementData = statement.allData;
				
				
					
					
					if("emailAddress" in statementData) {
						
						var emailAddress = statementData["emailAddress"];
						displayHTML += "<li role'listitem'><a class='email' title='email' href='mailto:'" + emailAddress + "' itemprop='email'>" + emailAddress + "</a></li>" ;
					}
					
				
				//org, outerOrg, position, middleOrg are all URLs so those can be included if need be
				displayHTML += "<span style='font-size:0.825em'>* " + externalSourceLabel + "</span></li>";
			}
		}
		return displayHTML;
	}
	
 
});


