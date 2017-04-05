<#-- $This file is distributed under the terms of the license in /doc/license.txt$ -->
<#--Where is external URI Info defined, actually passed to the template -->
<#-- List of positions for the individual -->
<#import "lib-external-properties.ftl" as extp_pos>
<#assign positions = propertyGroups.pullProperty("${core}relatedBy", "${core}Position")!>
<#if positions?has_content> <#-- true when the property is in the list, even if not populated (when editing) -->
    <#assign localName = positions.localName>
    <h2 id="${localName}" class="mainPropGroup" title="${positions.publicDescription!}">${positions.name?capitalize} <@p.addLink positions editable /> <@p.verboseDisplay positions /></h2>
    <ul id="individual-personInPosition" role="list">
        <@p.objectProperty positions editable />
        <@extp_pos.outputPositionInfo externalURIInfo positions />
    </ul> 
</#if> 
