# Fusion360API Python Addin
import adsk.core
import adsk.fusion
import traceback
import json
# import itertools
from .Timeline_Manager import getBodiesTree

handlers = []
_app: adsk.core.Application = None
_ui: adsk.core.UserInterface = None

_cmdInfo = {
    'id': 'KANTOKU_HistoryTree',
    'name': 'HistoryTree',
    'tooltip': 'HistoryTree',
    'resources': ''
}

_paletteInfo = {
    'id': 'KANTOKU_HistoryTree_Palette',
    'name': 'History Tree',
    'htmlFileURL': '.\html\index.html',
    'isVisible': True,
    'showCloseButton': True,
    'isResizable': True,
    'width': 500,
    'height': 550,
    'useNewWebBrowser': True,
    'dockingState': '',
}

# _nodeDict = {}
# _edgeLst = []
_treeJson = {}

class MyHTMLEventHandler(adsk.core.HTMLEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            htmlArgs = adsk.core.HTMLEventArgs.cast(args)

            global _app
            if htmlArgs.action == 'htmlLoaded':
                # global _nodeDict, _edgeLst

                # nodeDataDict = {}
                # for key in _nodeDict.keys():
                #     nodeDataDict[_nodeDict[key]['id']] = {
                #         'label' : _nodeDict[key]['label']
                #     }

                global _treeJson
                data = {
                    'data': list(_treeJson.values())
                }

                # data = {
                #     'data': {
                #         'id': 'root',
                #         'text': 'root',
                #         'children': list(_treeJson.values())
                #     }
                # }
                args.returnData = json.dumps(data)

        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class ShowPaletteCommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            global _ui, _paletteInfo

            palette: adsk.core.Palette = _ui.palettes.itemById(_paletteInfo['id'])
            if palette:
                palette.deleteMe()

            palette = _ui.palettes.add(
                _paletteInfo['id'],
                _paletteInfo['name'],
                _paletteInfo['htmlFileURL'],
                _paletteInfo['isVisible'],
                _paletteInfo['showCloseButton'],
                _paletteInfo['isResizable'],
                _paletteInfo['width'],
                _paletteInfo['height'],
                _paletteInfo['useNewWebBrowser'],
            )

            if len(_paletteInfo['dockingState']) > 0:
                palette.dockingState = _paletteInfo['dockingState']

            onHTMLEvent = MyHTMLEventHandler()
            palette.incomingFromHTML.add(onHTMLEvent)
            handlers.append(onHTMLEvent)

            onClosed = MyCloseEventHandler()
            palette.closed.add(onClosed)
            handlers.append(onClosed)

            onActivate = MyActivateHandler()
            args.command.activate.add(onActivate)
            handlers.append(onActivate)

            # timeline data
            global _treeJson
            _treeJson = getBodiesTree()

        except:
            _ui.messageBox('Command executed failed: {}'.format(traceback.format_exc()))


class MyCloseEventHandler(adsk.core.UserInterfaceGeneralEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            pass
        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class MyActivateHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args: adsk.core.CommandEventArgs):
        global _ui
        palette = _ui.palettes.itemById(_paletteInfo['id'])

        # palette.sendInfoToHTML(
        #     'test',
        #     '10'
        # )


class ShowPaletteCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            command = args.command
            onExecute = ShowPaletteCommandExecuteHandler()
            command.execute.add(onExecute)
            handlers.append(onExecute)

            onActivate = MyActivateHandler()
            command.activate.add(onActivate)
            handlers.append(onActivate)

        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def run(context):
    try:
        global _ui, _app
        _app = adsk.core.Application.get()
        _ui  = _app.userInterface
        
        global _cmdInfo
        showPaletteCmdDef = _ui.commandDefinitions.itemById(_cmdInfo['id'])
        if showPaletteCmdDef:
            showPaletteCmdDef.deleteMe()

        showPaletteCmdDef = _ui.commandDefinitions.addButtonDefinition(
            _cmdInfo['id'],
            _cmdInfo['name'],
            _cmdInfo['tooltip'],
            _cmdInfo['resources']
        )

        onCommandCreated = ShowPaletteCommandCreatedHandler()
        showPaletteCmdDef.commandCreated.add(onCommandCreated)
        handlers.append(onCommandCreated)
        
        panel = _ui.allToolbarPanels.itemById('SolidScriptsAddinsPanel')
        cntrl = panel.controls.itemById('showPalette')
        if not cntrl:
            panel.controls.addCommand(showPaletteCmdDef)

    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def stop(context):
    try:
        global _paletteInfo
        palette = _ui.palettes.itemById(_paletteInfo['id'])
        if palette:
            palette.deleteMe()
            
        global _cmdInfo
        panel = _ui.allToolbarPanels.itemById('SolidScriptsAddinsPanel')
        cmd = panel.controls.itemById(_cmdInfo['id'])
        if cmd:
            cmd.deleteMe()
        cmdDef = _ui.commandDefinitions.itemById(_cmdInfo['id'])
        if cmdDef:
            cmdDef.deleteMe()
            
        _app.log('Stop addin')
    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))