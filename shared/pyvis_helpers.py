"""
Shared PyVis helpers.

Common post-processing applied to every interactive vis.js network on the
platform so they all share the same dark theme, HTML tooltip support, auto-fit
behaviour and Ctrl/Cmd + scroll zoom interaction (the page can scroll over the
network without trapping the wheel).
"""

import base64
import streamlit as st
import streamlit.components.v1 as components


def render_pyvis_html(html: str, height: int = 640):
    """Embed a PyVis-generated HTML document inside the Streamlit page.

    Uses `st.iframe` when available, and falls back to the stable
    components API on older Streamlit versions that do not expose it.
    """
    encoded = base64.b64encode(html.encode("utf-8")).decode("ascii")
    iframe = getattr(st, "iframe", None)
    if callable(iframe):
        iframe(f"data:text/html;base64,{encoded}", height=height)
        return

    components.html(html, height=height, scrolling=False)


def apply_pyvis_post_processing(html: str) -> str:
    """Inject dark theme CSS, HTML-tooltip support, auto-fit, and
    Ctrl/Cmd-scroll zoom into a PyVis-generated HTML string."""
    tooltip_css = """
    <style>
      html, body { background-color: #0F1117 !important; margin: 0; padding: 0; }
      .card { background-color: #0F1117 !important; border: none !important;
              box-shadow: none !important; margin: 0 !important; padding: 0 !important; }
      .card-body { background-color: #0F1117 !important; padding: 0 !important;
                   overflow: hidden !important; }
      #mynetwork { background-color: #0F1117 !important; overflow: hidden !important;
                   border: none !important; }
      div.vis-tooltip {
        background-color: #1A1D27 !important;
        border: 1px solid #2A2D3A !important;
        color: #F9FAFB !important;
        font-family: 'IBM Plex Sans', sans-serif !important;
        font-size: 12px !important;
        line-height: 1.55 !important;
        padding: 8px 12px !important;
        border-radius: 6px !important;
        max-width: 280px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5) !important;
      }
      div.vis-tooltip b { color: #F9FAFB; }
    </style>
    """
    tooltip_js = """
        function _htmlTitle(text) {
          if (typeof text === 'string' && text.indexOf('<') > -1) {
            var div = document.createElement('div');
            div.innerHTML = text;
            return div;
          }
          return text;
        }
        nodes.get().forEach(function(n) {
          if (n.title) nodes.update({id: n.id, title: _htmlTitle(n.title)});
        });
        edges.get().forEach(function(e) {
          if (e.title) edges.update({id: e.id, title: _htmlTitle(e.title)});
        });
        """
    post_init_js = """
        network.once("stabilizationIterationsDone", function() {
          network.fit({animation: {duration: 600, easingFunction: "easeInOutCubic"}});
          // Freeze physics so the network stops drifting once stabilised.
          // Dragging still works (vis.js handles drag independently of physics).
          network.setOptions({physics: {enabled: false}});
        });
        network.setOptions({interaction: {zoomView: false}});

        var _netContainer = document.getElementById('mynetwork');
        _netContainer.style.position = 'relative';

        var _isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
        var _zoomHint = document.createElement('div');
        _zoomHint.style.cssText =
          'position:absolute; left:50%; top:50%; transform:translate(-50%,-50%);' +
          'background:rgba(15,17,23,0.92); color:#F9FAFB; padding:10px 18px;' +
          'border-radius:6px; font-family:"IBM Plex Sans",sans-serif;' +
          'font-size:13px; pointer-events:none; opacity:0;' +
          'transition:opacity 0.25s; z-index:1000; white-space:nowrap;' +
          'border:1px solid #2A2D3A;';
        _zoomHint.textContent = 'Hold ' + (_isMac ? '⌘' : 'Ctrl') + ' + scroll to zoom';
        _netContainer.appendChild(_zoomHint);

        var _hintTimer = null;
        _netContainer.addEventListener('wheel', function(e) {
          if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            var scale = network.getScale();
            var direction = e.deltaY < 0 ? 1.1 : 1 / 1.1;
            var newScale = Math.max(0.4, Math.min(3.0, scale * direction));
            network.moveTo({scale: newScale, animation: false});
          } else {
            _zoomHint.style.opacity = '1';
            if (_hintTimer) clearTimeout(_hintTimer);
            _hintTimer = setTimeout(function() {
              _zoomHint.style.opacity = '0';
            }, 800);
          }
        }, { passive: false });
        """

    html = html.replace("</head>", tooltip_css + "</head>")
    html = html.replace(
        "network = new vis.Network(container, data, options);",
        tooltip_js
        + "\n        network = new vis.Network(container, data, options);\n"
        + post_init_js,
    )
    return html
