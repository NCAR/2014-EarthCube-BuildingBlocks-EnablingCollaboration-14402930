<#-- $This file is distributed under the terms of the license in /doc/license.txt$ -->

<#-----------------------------------------------------------------------------
    Macros and functions for working with properties and property lists
------------------------------------------------------------------------------>
<#macro externalObjectProperty rangeClass property editable template=property.template>
    <#--Start out simple, then we can try and utilize the same template code as the regular template to display properties-->
    <#-- First, check and see if there is an external property we want displayed here-->
    <#local externalContent = getExternalPropertyInfo() >
    <#if externalContent?has_content>
     	<@outputExternalURIInfo externalContent rangeClass property />
     </#if>
   
</#macro>

<#function getExternalPropertyInfo>
	<#local returnInfo = "" />
    <#if externalURIInfo?has_content>
 		<#local returnInfo = externalURIInfo />
 	</#if>	
 		
 		
	<#return returnInfo>
</#function>

<#function hasExternalInfo>
	<#local extInfo = getExternalPropertyInfo() />
	<#if extInfo?has_content>
		<#return true>
	</#if>
	<#return false>
</#function>

<#function hasExternalInfoForProperty propertyURI domainURI="" rangeURI="">
<#local extInfo = getExternalPropertyInfo() />
	<#local hasPropertyInfo = false/>
	
	<#if extInfo?has_content>
		<#list extInfo as extInfoItem>
				<#local iPropertyURI = extInfoItem.propertyURI />
				<#local iPropertyDomainURI = extInfoItem.propertyDomainURI />
				<#local iPropertyRangeURI = extInfoItem.propertyRangeURI />
				<#if iPropertyURI?has_content && iPropertyURI == propertyURI>
					<#if iPropertyDomainURI?has_content && iPropertyRangeURI?has_content && domainURI != "" && rangeURI != "">
						<#if domainURI == iPropertyDomainURI && rangeURI == iPropertyRangeURI >
							<#local hasPropertyInfo = true />
						</#if>
					<#else>
					<#-- property domain uri and range uris are not be to compared as they don't exist but property uri matches -->
						<#local hasPropertyInfo = true />
					</#if>
				</#if>
		</#list>
	</#if>
	
	
	<#return hasPropertyInfo>

</#function>
<#--externalURIInfo is array of POJOS-->
<#macro outputExternalURIInfo externalURIInfo rangeClass property>	
		<#list externalURIInfo as externalURIInfoItem>		
				<#local displayExternalInfo = getExternalInfoForProperty(externalURIInfoItem, property) />

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
			<li class="li-indicator" externalURI="${externalURI!}" propertyURI="${property.uri!}" domainURI="${property.domainUri!}" rangeURI="${property.rangeUri!}">	            
					<div>
    				<img id="loadingIndicator" class="indicator" src="${urls.base}/images/indicatorWhite.gif" alt="${i18n().processing_indicator}"/>
    				</div>
    		</li>
					<li class="hidden subclass external-property-list-item" role="listitem"  externalURI="${externalURI!}"  externalServiceURL="${serviceURL!}" 
		                propertyURI="${property.uri!}" domainURI="${property.domainUri!}" rangeURI="${property.rangeUri!}" externalBaseURL="${externalBaseURL!}"
		                sourceLabel="${label}">
		                &nbsp;
			       	</li>
	            </#if>
    	</#list>

</#macro>

<#function getExternalInfoForProperty externalURIInfoItem property>
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
	<#return displayExternalInfo>
</#function>
<#-- output position information -->
<#macro outputPositionInfo externalURIInfo property>
<#list externalURIInfo as externalURIInfoItem>		
	<#local displayExternalInfo = getExternalInfoForProperty(externalURIInfoItem, property) />
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
			<li class="li-indicator" externalURI="${externalURI!}" propertyURI="${property.uri!}" domainURI="${property.domainUri!}" rangeURI="${property.rangeUri!}">	            
					<div>
    				<img id="loadingIndicator" class="indicator" src="${urls.base}/images/indicatorWhite.gif" alt="${i18n().processing_indicator}"/>
    				</div>
    		</li>
			<li class="hidden external-property-list-item" role="listitem"  externalURI="${externalURI!}"  externalServiceURL="${serviceURL!}" 
	            propertyURI="${property.uri!}" domainURI="${property.domainUri!}" rangeURI="${property.rangeUri!}" externalBaseURL="${externalBaseURL!}"
	            sourceLabel="${label}">
	       	</li>
        </#if>
</#list>
</#macro>

<#--output contact info, obviously cleanup possible -->
<#macro outputContactInfo externalURIInfo property>
<#list externalURIInfo as externalURIInfoItem>		
	
	<#local displayExternalInfo = getExternalInfoForProperty(externalURIInfoItem, property) />
	
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
			<li class="li-indicator" externalURI="${externalURI!}" propertyURI="${property.uri!}" domainURI="${property.domainUri!}" rangeURI="${property.rangeUri!}">	            
					<div>
    				<img id="loadingIndicator" class="indicator" src="${urls.base}/images/indicatorWhite.gif" alt="${i18n().processing_indicator}"/>
    				</div>
    		</li>
			<li class="hidden external-property-list-item" role="listitem"  externalURI="${externalURI!}"  externalServiceURL="${serviceURL!}" 
	            propertyURI="${property.uri!}" domainURI="${property.domainUri!}" rangeURI="${property.rangeUri!}" externalBaseURL="${externalBaseURL!}"
	            sourceLabel="${label}">&nbsp;</li>
	      <#else>
	      	
        </#if>
</#list>
</#macro>

<#-- output icons for linked external profiles -->
<#-- May deal with this client side instead -->
<#--macro displayLinkedProfilesWithIcons >
	<#local externalInfo = lext.getExternalPropertyInfo() />
	<#local externalURIHash = {} />
	<#list externalURIInfo as externalURIInfoItem>	
			
	</#list>
	
</#macro-->