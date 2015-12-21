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
		<#list externalURIInfo as externalURIInfoItem>
				<#local propertyURI = externalURIInfoItem.propertyURI />
				<#local propertyDomainURI = externalURIInfoItem.propertyDomainURI />
				<#local propertyRangeURI = externalURIInfoItem.propertyRangeURI />
				
				<#local displayExternalInfo = false />
				<#-- If no propertyURI, domain or range URI has been specified,  don't display anything, but we could also do the opposite, depends on how this needs to be-->
				<#if propertyURI?has_content>
					<#if propertyDomainURI?has_content && propertyRangeURI?has_content>
						<#if (property.domainUri)?? && property.domainUri == propertyDomainURI &&
						(property.rangeUri)?? && property.rangeUri == propertyRangeURI>
							<#local displayExternalInfo = true>
						</#if>
					<#else>
						<#-- if no domain and range specified for external entity retrieval, get the info back -->
						<#local displayExternalInfo = true>
					</#if>
				</#if>
				<#if displayExternalInfo>
					<#--Used to call out external properties separately, here interleaving-->
					<#local label = "" />
					<#local serviceURL = ""/>
					<#local externalBaseURL = ""/>				
					<#local externalURI = externalURIInfoItem.externalURI />
					<#local serviceName = externalURIInfoItem.externalServiceName />
					<#if externalURI?has_content && externalURIInfoItem.externalServiceURL?has_content>
						<#local externalBaseURL = externalURIInfoItem.externalServiceURL />
						<#local serviceURL = externalURIInfoItem.externalServiceURL + "/individual?uri=" + externalURI?url + "&action=defaultJSON" />
					</#if>
					<#if serviceName?has_content>
						<#local label = label + " (" + serviceName + ")" />
					</#if>
					<li class="subclass external-property-list-item" role="listitem"  externalURI="${externalURI!}"  externalServiceURL="${serviceURL!}" 
		                propertyURI="${property.uri!}" domainURI="${property.domainUri!}" rangeURI="${property.rangeUri!}" externalBaseURL="${externalBaseURL!}"
		                sourceLabel="${label}">
		                External Content
			       	</li>
	            </#if>
    	</#list>

</#macro>