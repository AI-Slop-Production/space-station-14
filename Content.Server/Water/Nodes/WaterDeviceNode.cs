using Content.Server.NodeContainer;
using Content.Server.NodeContainer.EntitySystems;
using Content.Server.NodeContainer.Nodes;
using Content.Shared.NodeContainer;
using Robust.Shared.Map.Components;

namespace Content.Server.Water.Nodes;

/// <summary>
/// Узел-устройство, подключающийся к водяной трубе под ним (на той же клетке).
/// </summary>
[DataDefinition]
public sealed partial class WaterDeviceNode : Node
{
    [DataField("enabled")] public bool Enabled { get; set; } = true;

    public override bool Connectable(IEntityManager entMan, TransformComponent? xform = null)
    {
        if (!Enabled)
            return false;
        return base.Connectable(entMan, xform);
    }

    public override IEnumerable<Node> GetReachableNodes(TransformComponent xform,
        EntityQuery<NodeContainerComponent> nodeQuery,
        EntityQuery<TransformComponent> xformQuery,
        MapGridComponent? grid,
        IEntityManager entMan)
    {
        if (!xform.Anchored || grid == null)
            yield break;

        var gridIndex = grid.TileIndicesFor(xform.Coordinates);

        foreach (var node in NodeHelpers.GetNodesInTile(nodeQuery, grid, gridIndex))
        {
            if (node is WaterPipeNode)
                yield return node;
        }
    }
}


