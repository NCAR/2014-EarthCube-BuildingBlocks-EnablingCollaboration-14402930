/* $This file is distributed under the terms of the license in /doc/license.txt$ */

package edu.cornell.mannlib.vitro.webapp.search.externallookup;

import org.apache.axis.utils.StringUtils;
import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;

import net.sf.json.JSONObject;






public class LookupResult  {
	private static final Log log = LogFactory.getLog(LookupResult.class);



private String label = ""; //the name or string we want represented
   private String typeString = ""; //this will be affixed to the end
   private String typeURI = ""; //in some cases, we may have an actual URI for the object
   private String idString = ""; //this is a string identifier in the case where we don't have a URI
   private String idURI = "";// in the case where an identifying URI is present
   private String serviceName = ""; //this will useful in case we are getting results from multiple services
   private String serviceURI = "";//if we have a URI representing the service, even better
   private JSONObject additionalInfo = null; //in the case where we have additional information that needs to be passed back in any case
   private JSONObject endpointInfo = null; //For a particular search result, need to include information about the endpoint from where the information can be retrieved
	/**
	 * @param additionalInfo
	 *            the additionalInfo to set
	 */
	public void setAdditionalInfo(JSONObject additionalInfo) {
		this.additionalInfo = additionalInfo;
	}

	/**
     *
     */
    public LookupResult(String label, String typeString, String typeURI, String idString,String idURI, String serviceName, String serviceURI) {
       
    	this.label = label;
       this.typeString = typeString;
       this.typeURI = typeURI;
       this.idString = idString;
       this.idURI = idURI;
       this.serviceName = serviceName;
       this.serviceURI = serviceURI;
     
    }

    /*
     * Getters
     */
    
   

	/**
	 * @return the typeString
	 */
	public String getTypeString() {
		return typeString;
	}

	/**
	 * @return the typeURI
	 */
	public String getTypeURI() {
		return typeURI;
	}

	/**
	 * @return the idString
	 */
	public String getIdString() {
		return idString;
	}

	/**
	 * @return the idURI
	 */
	public String getIdURI() {
		return idURI;
	}

	/**
	 * @return the serviceURI
	 */
	public String getServiceURI() {
		return serviceURI;
	}

	/**
	 * @return the additionalInfo
	 */
	public JSONObject getAdditionalInfo() {
		return additionalInfo;
	}

	public String getLabel() {
    	return this.label;
    }
    
  
    
    public String getServiceName() {
    	return this.serviceName;
    }
    
  
    
    public JSONObject toJSONObject() {
    	JSONObject jsonObj = new JSONObject();
    	try {
    	 jsonObj.put("label", label);
         jsonObj.put("idString", idString);
         jsonObj.put("uri", idURI);
         jsonObj.put("typeString", typeString);
         jsonObj.put("typeURI", typeURI);
         jsonObj.put("additionalInfo", additionalInfo);
         jsonObj.put("serviceName", serviceName);
         jsonObj.put("serviceURI", serviceURI);
         jsonObj.put("endpointInfo", endpointInfo);
    	} catch(Exception ex) {
    		log.error("Error occurred in converting values to JSON object", ex);
    	}
    	return jsonObj;
    }

	public JSONObject getEndpointInfo() {
		return endpointInfo;
	}

	public void setEndpointInfo(JSONObject endpointInfo) {
		this.endpointInfo = endpointInfo;
	}

    
}
