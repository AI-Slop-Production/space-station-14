using Content.Server.NodeContainer;
using Content.Server.Water.NodeGroups;
using Content.Shared.NodeContainer.NodeGroups;

namespace Content.Server.Water.Components;

[RegisterComponent]
public sealed partial class WaterConsumerComponent : Component
{
    [DataField("desiredFlowPerSecond")] public float DesiredFlowPerSecond = 10f;
    [DataField("node")] public string? NodeName;

    [ViewVariables] public float ReceivedLastSecond;
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
                net.AddConsumer(this);
                return;
            }
        }
    }

    public void DetachFromNet()
    {
        if (Net != null)
        {
            Net.RemoveConsumer(this);
            Net = null;
        }
    }
}


