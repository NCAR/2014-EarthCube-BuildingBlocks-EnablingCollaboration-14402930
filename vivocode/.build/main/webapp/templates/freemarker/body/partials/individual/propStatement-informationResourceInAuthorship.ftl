<#-- $This file is distributed under the terms of the license in /doc/license.txt$ -->

<#-- Custom object property statement view for faux property "authors". See the PropertyConfig.3 file for details. 
    
     This template must be self-contained and not rely on other variables set for the individual page, because it
     is also used to generate the property statement during a deletion.  
 -->

<#import "lib-sequence.ftl" as s>
<@showAuthorship statement />

<#-- Use a macro to keep variable assignments local; otherwise the values carry over to the
     next statement -->
<#macro showAuthorship statement>
    <#if statement.author??>
    	<#if statement.subclass?? && statement.subclass?contains("vcard")>
        	${statement.authorName}
    	<#else>
        	<a href="${profileUrl(statement.uri("author"))}" title="${i18n().author_name}">${statement.authorName}</a>
    	</#if>
    <#else>
        <#-- This shouldn't happen, but we must provide for it -->
        <a href="${profileUrl(statement.uri("authorship"))}" title="${i18n().missing_author}">${i18n().missing_author}</a>
    </#if>
</#macro>