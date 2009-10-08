function addVNC(hostname, virtname, port, divnum, popup) {
    var vnc_div = document.getElementById('vncDiv' + divnum)
    var newvnc = document.createElement('vncWindow' + divnum)
    var vnclink = document.getElementById('vncLink' + divnum)
    //uggy hardcoded html bits here
    var applethtml = "<APPLET CODE=VncViewer.class ARCHIVE=/static/applets/VncViewer.jar WIDTH=800 HEIGHT=500>\
        <PARAM NAME=\"HOST\" VALUE=\""+hostname+"\">\
        <PARAM NAME=\"PORT\" VALUE="+port+">\
    </APPLET>"
    var closelink = "<a href=\"javascript:;\" onclick=\"removeVNC(\'"+hostname+
        "\',\'"+virtname+"\',\'"+port+"\',\'"+divnum+"\');\">Close VNC Console</a>"
    if(popup=='1'){ //popup window
        var popup = window.open("", virtname, "width=825,height=525,scrollbars=no")
        popup.document.writeln('<html><head><title>'+virtname+'</title></head><body>')
        popup.document.writeln(applethtml)
        popup.document.writeln('</body></html>')
    }
    else{ //inline window
        vnc_div.removeChild(vnclink)
        newvnc.setAttribute('id', 'vncWindow' + divnum)
        newvnc.innerHTML = ""+closelink+applethtml
        vnc_div.appendChild(newvnc)
    }
}

function removeVNC(hostname, virtname, port, divnum) {
    var vnc_div = document.getElementById('vncDiv' + divnum)
    var vncwindow = document.getElementById('vncWindow' + divnum)
    vnc_div.removeChild(vncwindow)
    var vnclink = document.createElement('vncLink' + divnum)
    var popuplink =  '<a href="javascript:;" onclick="addVNC(\''+hostname+
        '\',\''+virtname+'\',\''+port+'\',\''+divnum+'\',\'1\');">Open VNC Console (in popup)</a>'
    var inlinelink =  '<a href="javascript:;" onclick="addVNC(\''+hostname+
        '\',\''+virtname+'\',\''+port+'\',\''+divnum+'\',\'0\');">Open VNC Console (inline)</a>'
    vnclink.setAttribute('id', 'vncLink' + divnum)
    vnclink.innerHTML = popuplink + ' | ' + inlinelink 
    vnc_div.appendChild(vnclink)
}
