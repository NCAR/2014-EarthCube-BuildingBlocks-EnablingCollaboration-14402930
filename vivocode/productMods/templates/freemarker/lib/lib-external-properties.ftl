<#-- $This file is distributed under the terms of the license in /doc/license.txt$ -->

<#-----------------------------------------------------------------------------
    Macros and functions for working with properties and property lists
------------------------------------------------------------------------------>
<#macro externalObjectProperty rangeClass property editable template=property.template>
    <#--Start out simple, then we can try and utilize the same template code as the regular template to display properties-->
    <#-- First, check and see if there is an external property we want displayed here-->
    <#local externalContent = getExternalPropertyInfo(property) >
    <#if externalContent?has_content>
     	<@outputExternalURIInfo externalContent rangeClass property />
     </#if>
   
</#macro>

<#function getExternalPropertyInfo property>
	<#local returnInfo = "" />
    <#if externalURIInfo?has_content>
 		<#local returnInfo = externalURIInfo />
 	</#if>	
 		
 		
	<#return returnInfo>
</#function>

<#--externalURIInfo is array of POJOS-->
<#macro outputExternalURIInfo externalURIInfo rangeClass property>
	<#--Hard coding but this should come from template-->
	<#if rangeClass == "Authorship" && (property.domainUri)?? && property.domainUri?contains("Person")>
		<#local label = "External " + property.name />
		<#local serviceURL = ""/>
		<#local externalBaseURL = ""/>
		<#list externalURIInfo as externalURIInfoItem>
			<#local externalURI = externalURIInfoItem.externalURI />
			<#local serviceName = externalURIInfoItem.externalServiceName />
			<#if externalURI?has_content && externalURIInfoItem.externalServiceURL?has_content>
				<#local externalBaseURL = externalURIInfoItem.externalServiceURL />
				<#local serviceURL = externalURIInfoItem.externalServiceURL + "/individual?uri=" + externalURI?url + "&action=defaultJSON" />
			</#if>
			<#if serviceName?has_content>
				<#local label = label + " (" + serviceName + ")" />
			</#if>
			<li class="subclass" role="listitem">
	                <h3>${label}</h3>
	                <ul class="subclass-property-list external-property-list" externalURI="${externalURI!}"  externalServiceURL="${serviceURL!}" 
	                propertyURI="${property.uri!}" domainURI="${property.domainUri!}" rangeURI="${property.rangeUri!}" externalBaseURL="${externalBaseURL!}">
	                    
	                </ul>
	            </li>
    	</#list>
	</#if>
</#macro>