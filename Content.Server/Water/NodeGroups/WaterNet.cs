using Content.Server.NodeContainer.NodeGroups;
using Content.Server.NodeContainer.Nodes;
using Content.Server.Water.Components;
using Content.Shared.NodeContainer;
using Content.Shared.NodeContainer.NodeGroups;

namespace Content.Server.Water.NodeGroups;

public interface IWaterNet : INodeGroup
{
    void AddReservoir(WaterReservoirComponent reservoir);
    void RemoveReservoir(WaterReservoirComponent reservoir);
    void AddConsumer(WaterConsumerComponent consumer);
    void RemoveConsumer(WaterConsumerComponent consumer);
}

[NodeGroup(NodeGroupID.Water)]
public sealed class WaterNet : BaseNodeGroup, IWaterNet
{
    public readonly List<WaterReservoirComponent> Reservoirs = new();
    public readonly List<WaterConsumerComponent> Consumers = new();

    public void AddReservoir(WaterReservoirComponent reservoir)
    {
        if (!Reservoirs.Contains(reservoir))
            Reservoirs.Add(reservoir);
    }

    public void RemoveReservoir(WaterReservoirComponent reservoir)
    {
        Reservoirs.Remove(reservoir);
    }

    public void AddConsumer(WaterConsumerComponent consumer)
    {
        if (!Consumers.Contains(consumer))
            Consumers.Add(consumer);
    }

    public void RemoveConsumer(WaterConsumerComponent consumer)
    {
        Consumers.Remove(consumer);
    }
}


