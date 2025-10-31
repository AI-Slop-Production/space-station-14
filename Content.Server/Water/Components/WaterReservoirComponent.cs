using Content.Server.NodeContainer;
using Content.Server.Water.NodeGroups;
using Content.Shared.NodeContainer.NodeGroups;

namespace Content.Server.Water.Components;

[RegisterComponent]
public sealed partial class WaterReservoirComponent : Component
{
    [DataField("capacity")] public float Capacity = 1000f; // литров
    [DataField("currentVolume")] public float CurrentVolume = 1000f;
    [DataField("maxOutputPerSecond")] public float MaxOutputPerSecond = 50f;
    [DataField("node")] public string? NodeName;

    [ViewVariables] public IWaterNet? Net;

    public void TryAttachToNet(IEntityManager entMan)
    {
        if (!entMan.TryGetComponent(Owner, out NodeContainerComponent? container))
            return;

        foreach (var node in container.Nodes.Values)
        {
            if (NodeName != null && node.Name != NodeName)
                continue;
            if (node.NodeGroupID != NodeGroupID.Water)
                continue;
            if (node.NodeGroup is IWaterNet net)
            {
                Net = net;
                net.AddReservoir(this);
                return;
            }
        }
    }

    public void DetachFromNet()
    {
        if (Net != null)
        {
            Net.RemoveReservoir(this);
            Net = null;
        }
    }
}


