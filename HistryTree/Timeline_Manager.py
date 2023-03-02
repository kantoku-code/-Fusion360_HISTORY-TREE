import traceback
import adsk.fusion as fusion
import adsk.core as core
# import itertools
import json

TEST = False
TEST_COUNT = 12

def run(context):
    ui = core.UserInterface.cast(None)
    try:
        app: core.Application = core.Application.get()
        ui = app.userInterface

        dict = getBodiesTree()

        print(json.dumps(dict, indent=2, ensure_ascii=False))
        app.log(f'{json.dumps(dict, indent=2, ensure_ascii=False)}')

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def getBodiesTree() -> dict:
    '''
    履歴をDictで取得
    '''

    # Expansion
    fusion.ExtrudeFeature.getRefs = getReferences_Extrude
    fusion.RevolveFeature.getRefs = getReferences_Extrude
    fusion.LoftFeature.getRefs = getReferences_Loft
    fusion.SweepFeature.getRefs = getReferences_Sweep
    fusion.HoleFeature.getRefs = getReferences_Hole

    fusion.CombineFeature.getRefs = getReferences_Combine

    fusion.Feature.isBoolOpe = is_boolen_operation

    # ************
    def initBodyInfo(body: fusion.BRepBody) -> dict:
        return {
            'id' : body.entityToken,
            'text' : body.name,
            # 'icon' : '',
            'children' : [],
        }

    def initFeatureInfo(feat: fusion.Feature) -> dict:
        if hasattr(feat, 'getRefs'):
            children = feat.getRefs()
        else:
            children = []

        return {
            'id' : feat.entityToken,
            'text' : feat.name,
            # 'icon' : '',
            'children' : children,
        }

    # ******
    app: core.Application = core.Application.get()
    des: fusion.Design = app.activeProduct

    timeline: fusion.Timeline = des.timeline
    backupMarker = timeline.markerPosition

    bodiesDict = {}

    timeObjs = [timeline.item(idx) for idx in range(timeline.count)]

    if TEST:
        timeObjs = timeObjs[:TEST_COUNT]

    for timeObj in timeObjs:
        timeObj: fusion.TimelineObject

        feat: fusion.Feature = fusion.Feature.cast(timeObj.entity)
        if not feat:
            continue

        timeObj.rollTo(False)
        afterBodies = get_all_bodies()

        if not hasattr(feat, 'bodies'):
            continue

        bodyInfos = [initBodyInfo(b) for b in feat.bodies]
        [bodiesDict.setdefault(info['id'], info) for info in bodyInfos]

        timeObj.rollTo(True)
        if feat.classType() == fusion.CombineFeature.classType():
            # 結合
            for info in bodyInfos:
                children = []
                featInfo = initFeatureInfo(feat)
                for token in featInfo['children']:
                    children.append(bodiesDict[token])
                    bodiesDict.pop(token)
                featInfo['children'] = children
                bodiesDict[info['id']]['children'].append(featInfo)

        else:
            # その他
            featInfo = initFeatureInfo(feat)

            # オペレーションで結合等を使った場合
            if feat.isBoolOpe():
                removeBodies = diff_list_by_entity(get_all_bodies(), afterBodies)

                for body in removeBodies:
                    token = body.entityToken
                    featInfo['children'].append(bodiesDict[token])
                    bodiesDict.pop(token) 

            # オペレーションでボディが分割された場合の表示が不完全
            [bodiesDict[info['id']]['children'].append(featInfo) for info in bodyInfos]

    timeline.markerPosition = backupMarker

    return bodiesDict


# 全てのボディ取得
def get_all_bodies() -> list:
    '''
    全てのボディ取得
    '''
    app: core.Application = core.Application.get()
    des: fusion.Design = app.activeProduct

    comp: fusion.Component = None
    bodyLst = []
    for comp in des.allComponents:
        bodyLst.extend([b for b in comp.bRepBodies])

    return bodyLst


# オペレーションがNewでは無いタイプ
def is_boolen_operation(
    self: fusion.Feature
) -> bool:
    '''
    ボディの増減を確認
    '''

    if not hasattr(self, 'operation'):
        return False

    boolenTypes = [
        fusion.FeatureOperations.JoinFeatureOperation,
        fusion.FeatureOperations.CutFeatureOperation,
        fusion.FeatureOperations.IntersectFeatureOperation,
    ]

    return self.operation in boolenTypes

# def getBodies() -> list:
#     app: core.Application = core.Application.get()
#     des: fusion.Design = app.activeProduct

#     bodiesList = [c.bRepBodies for c in des.allComponents]
#     bodyList = []
#     for bodies in bodiesList:
#         bodyList.extend([b for b in bodies])

#     bodyInfos = []
#     for body in bodyList:
#         bodyInfos.append(
#             {
#                 'id' : body.entityToken,
#                 'text' : body.name,
#             }
#         )

#     return bodyInfos


# 'adsk::fusion::RevolveFeature'
# 'adsk::fusion::ExtrudeFeature'
def getReferences_Extrude(self):
    '''
    押し出し・回転用
    '''

    def getParentEntity(prof):
        if hasattr(prof, 'parentSketch'):
            return prof.parentSketch.name
        else:
            return

    parent = None
    try:
        prof = self.profile
        if hasattr(prof, '__iter__'):
            profs = [getParentEntity(p) for p in self.profile]
            parent = list(set(profs))
        else:
            parent = [getParentEntity(prof)]
    except:
        parent = []

    return parent


# 'adsk::fusion::LoftFeature'
def getReferences_Loft(self) -> list:
    '''
    ロフト用
    '''

    def getAllReference() -> list:
        refs = []

        for groupName in ['loftSections', 'centerLineOrRails']:
            try:
                group = getattr(self, groupName)
                refs.extend(e for e in group)
            except:
                continue

        return refs

    def getParent(sect) -> str:
        try:
            return sect.entity.parentSketch.name
        except:
            return None

    parent = None
    try:
        sections = getAllReference()
        refs = removeBlanks([getParent(s) for s in sections])
        parent = list(set(refs))
    except:
        parent = []

    return parent


# 'adsk::fusion::SweepFeature'
def getReferences_Sweep(self) -> list:
    '''
    スイープ用
    '''

    def getParent(ent) -> str:
        try:
            return ent.parentSketch.name
        except:
            return None

    parent = []
    # profile
    try:
        prof = self.profile
        if hasattr(prof, '__iter__'):
            profs = [getParent(p) for p in self.profile]
            parent = list(set(profs))
        else:
            parent = [getParent(prof)]
    except:
        pass

    #     parent.append(getParent(self.profile))
    # except:
    #     pass

    # path
    try:
        prof = self.profile
        if hasattr(prof, '__iter__'):
            profs = [getParent(p) for p in self.profile]
            parent.extend(list(set(profs)))
        else:
            parent.extend([getParent(prof)])
    except:
        pass


    #     parent.extend([getParent(p.entity) for p in self.path])
    # except:
    #     pass

    return list(set(parent))


# 'adsk::fusion::HoleFeature'
def getReferences_Hole(self) -> list:
    '''
    穴用
    '''

    def getParent(ent) -> str:
        try:
            return ent.parentSketch.name
        except:
            return None

    parent = []
    try:
        points: core.ObjectCollection = self.holePositionDefinition.sketchPoints
        parent.extend([getParent(p) for p in points])
    except:
        pass

    return list(set(parent))


# 'adsk::fusion::CombineFeature'
def getReferences_Combine(self) -> list:
    '''
    結合用
    '''
    parent = []
    for body in self.toolBodies:
        parent.append(body.entityToken)

    return parent


def removeBlanks(lst: list):
    return list(filter(lambda x: x is not None, lst))


def diff_list_by_entity(lst1: list, lst2: list) -> list:
    return [e for e in lst1 if not e in lst2]