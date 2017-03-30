<#-- $This file is distributed under the terms of the license in /doc/license.txt$ -->

<#-- Contact info on individual profile page -->
<#import "lib-external-properties.ftl" as clext>

<#assign phone = propertyGroups.pullProperty("http://purl.obolibrary.org/obo/ARG_2000028","http://www.w3.org/2006/vcard/ns#Telephone")!>
<#assign primaryEmail = propertyGroups.pullProperty("http://purl.obolibrary.org/obo/ARG_2000028","http://www.w3.org/2006/vcard/ns#Work")!>
<#assign addlEmail = propertyGroups.pullProperty("http://purl.obolibrary.org/obo/ARG_2000028","http://www.w3.org/2006/vcard/ns#Email")!>



<#if phone?has_content || primaryEmail?has_content || addlEmail?has_content >
    <ul style="font-size:1em;padding-bottom:4px"><li><strong>${i18n().contact_info}</strong></li></ul>
</#if>

<#-- Primary Email -->    
<@emailLinks "primaryEmail" primaryEmail />
<ul id ="external-primary-emails" class="individual-emails" role="list">
<@clext.outputContactInfo externalURIInfo primaryEmail />
	<#list externalURIInfo as externalURIInfoItem >
	<#assign pURI = externalURIInfoItem.propertyURI />
	<#assign pDomainURI = externalURIInfoItem.propertyDomainURI />
	<#assign pRangeURI = externalURIInfoItem.propertyRangeURI />
					
	
	<#-- If no propertyURI, domain or range URI has been specified,  don't display anything, but we could also do the opposite, depends on how this needs to be-->
	<#if pURI?has_content>
		<#if pDomainURI?has_content && pRangeURI?has_content>
			<#if (primaryEmail.domainUri)?? && primaryEmail.domainUri == pDomainURI &&
			(primaryEmail.rangeUri)?? && primaryEmail.rangeUri == pRangeURI>
				
			</#if>
		<#else>
			<#-- if no domain and range specified for external entity retrieval, get the info back -->
			
		</#if>
	</#if>
	</#list>

</ul>

<#-- Additional Emails --> 
<@emailLinks "email" addlEmail />   
<ul id ="external-additional-emails" class="individual-emails" role="list">
<@clext.outputContactInfo externalURIInfo addlEmail />
</ul>  
<#-- Phone --> 

<#if phone?has_content> <#-- true when the property is in the list, even if not populated (when editing) -->
    <@p.addLinkWithLabel phone editable />
    <#if phone.statements?has_content> <#-- if there are any statements -->
        <ul id="individual-phone" role="list" <#if editable>style="list-style:none;margin-left:0;"</#if>>
            <#list phone.statements as statement>
                <li role="listitem">
                    <span itemprop="telephone">${statement.number!}</span>
                    <@p.editingLinks "${phone.localName}" "${phone.name}" statement editable phone.rangeUri />
                </li>
            </#list>
             
    			
     			<@clext.outputContactInfo externalURIInfo phone />
     		
        </ul>
    </#if>
</#if>

<#-- Add a hidden div if phone, email or others don't have content -->

<#macro emailLinks property email>
    <#if property == "primaryEmail">
        <#local listId = "primary-email">
        <#local label = "${i18n().primary_email_capitalized}">
    <#else>
        <#local listId = "additional-emails">
        <#local label = "${i18n().additional_emails_capitalized}">
    </#if>     
    <#if email?has_content> <#-- true when the property is in the list, even if not populated (when editing) -->
        <@p.addLinkWithLabel email editable label/>
        <#if email.statements?has_content> <#-- if there are any statements -->
            <ul id="${listId}" class="individual-emails" role="list" <#if editable>style="list-style:none;margin-left:0;"</#if>>
                <#list email.statements as statement>
                    <li role="listitem">
                        <a itemprop="email" class="email" href="mailto:${statement.emailAddress!}" title="${i18n().email}">${statement.emailAddress!}</a>
                        <@p.editingLinks "${email.localName}" "${email.name}" statement editable email.rangeUri />
                    </li>
                </#list>
            </ul>
        </#if>
        
    </#if>
</#macro>
