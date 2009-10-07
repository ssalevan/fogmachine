function addVNC(hostname, port, divnum) {
    var vnc_div = document.getElementById('vncDiv' + divnum)
    var newvnc = document.createElement('vncWindow' + divnum)
    var vnclink = document.getElementById('vncLink' + divnum)
    vnc_div.removeChild(vnclink)
    newvnc.setAttribute('id', 'vncWindow' + divnum)
    newvnc.innerHTML = "<a href=\"javascript:;\" onclick=\"removeVNC(\'"+hostname+"\',\'"+port+"\',\'"+divnum+"\');\">Close VNC Console</a>\
    <APPLET CODE=VncViewer.class ARCHIVE=/static/applets/VncViewer.jar WIDTH=800 HEIGHT=500>\
        <PARAM NAME=\"HOST\" VALUE=\""+hostname+"\">\
        <PARAM NAME=\"PORT\" VALUE="+port+">\
    </APPLET>"
    vnc_div.appendChild(newvnc)
}

function removeVNC(hostname, port, divnum) {
    var vnc_div = document.getElementById('vncDiv' + divnum)
    var vncwindow = document.getElementById('vncWindow' + divnum)
    vnc_div.removeChild(vncwindow)
    var vnclink = document.createElement('vncLink' + divnum)
    vnclink.setAttribute('id', 'vncLink' + divnum)
    vnclink.innerHTML = '<a href="javascript:;" onclick="addVNC(\''+hostname+'\',\''+port+'\',\''+divnum+'\');">Open VNC Console</a>'
    vnc_div.appendChild(vnclink)
}
