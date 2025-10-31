using Content.Server.NodeContainer;
using Content.Server.NodeContainer.EntitySystems;
using Content.Server.NodeContainer.Nodes;
using Content.Server.NodeContainer.NodeGroups;
using Content.Shared.Atmos;
using Content.Shared.NodeContainer;
using Robust.Shared.Map.Components;
using Robust.Shared.Utility;

namespace Content.Server.Water.Nodes;

/// <summary>
///     Узел трубы воды. Соединяется с другими водяными трубами по направлениям.
/// </summary>
[DataDefinition]
public sealed partial class WaterPipeNode : Node, IRotatableNode
{
    [DataField("pipeDirection")] public PipeDirection OriginalPipeDirection;

    public PipeDirection CurrentPipeDirection { get; private set; }

    [DataField("connectionsEnabled")] private bool _connectionsEnabled = true;
    [ViewVariables(VVAccess.ReadWrite)] public bool ConnectionsEnabled
    {
        get => _connectionsEnabled;
        set
        {
            _connectionsEnabled = value;
            if (NodeGroup != null)
                IoCManager.Resolve<IEntityManager>().System<NodeGroupSystem>().QueueRemakeGroup((BaseNodeGroup) NodeGroup);
        }
    }

    [DataField("rotationsEnabled")] public bool RotationsEnabled { get; set; } = true;

    public override bool Connectable(IEntityManager entMan, TransformComponent? xform = null)
    {
        return _connectionsEnabled && base.Connectable(entMan, xform);
    }

    public override void Initialize(EntityUid owner, IEntityManager entMan)
    {
        base.Initialize(owner, entMan);
        if (!RotationsEnabled)
            return;
        var xform = entMan.GetComponent<TransformComponent>(owner);
        CurrentPipeDirection = OriginalPipeDirection.RotatePipeDirection(xform.LocalRotation);
    }

    bool IRotatableNode.RotateNode(in MoveEvent ev)
    {
        if (OriginalPipeDirection == PipeDirection.Fourway)
            return false;

        if (!RotationsEnabled)
        {
            if (CurrentPipeDirection == OriginalPipeDirection)
                return false;
            CurrentPipeDirection = OriginalPipeDirection;
            return true;
        }

        var old = CurrentPipeDirection;
        CurrentPipeDirection = OriginalPipeDirection.RotatePipeDirection(ev.NewRotation);
        return old != CurrentPipeDirection;
    }

    public override void OnAnchorStateChanged(IEntityManager entityManager, bool anchored)
    {
        if (!anchored)
            return;

        if (!RotationsEnabled)
        {
            CurrentPipeDirection = OriginalPipeDirection;
            return;
        }

        var xform = entityManager.GetComponent<TransformComponent>(Owner);
        CurrentPipeDirection = OriginalPipeDirection.RotatePipeDirection(xform.LocalRotation);
    }

    public override IEnumerable<Node> GetReachableNodes(TransformComponent xform,
        EntityQuery<NodeContainerComponent> nodeQuery,
        EntityQuery<TransformComponent> xformQuery,
        MapGridComponent? grid,
        IEntityManager entMan)
    {
        if (!xform.Anchored || grid == null)
            yield break;

        var pos = grid.TileIndicesFor(xform.Coordinates);

        for (var i = 0; i < PipeDirectionHelpers.PipeDirections; i++)
        {
            var pipeDir = (PipeDirection) (1 << i);
            if (!CurrentPipeDirection.HasDirection(pipeDir))
                continue;

            foreach (var pipe in PipesInDirection(pos, pipeDir, grid, nodeQuery))
            {
                if (pipe.NodeGroupID == NodeGroupID && pipe.CurrentPipeDirection.HasDirection(pipeDir.GetOpposite()))
                    yield return pipe;
            }
        }
    }

    private IEnumerable<WaterPipeNode> PipesInDirection(Vector2i pos, PipeDirection pipeDir, MapGridComponent grid,
        EntityQuery<NodeContainerComponent> nodeQuery)
    {
        var offsetPos = pos.Offset(pipeDir.ToDirection());
        foreach (var entity in grid.GetAnchoredEntities(offsetPos))
        {
            if (!nodeQuery.TryGetComponent(entity, out var container))
                continue;
            foreach (var node in container.Nodes.Values)
            {
                if (node is WaterPipeNode pipe)
                    yield return pipe;
            }
        }
    }
}


