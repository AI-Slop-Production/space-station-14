using Content.Server.NodeContainer.EntitySystems;
using Content.Server.Water.Components;

namespace Content.Server.Water.EntitySystems;

public sealed class WaterNetConnectorSystem : EntitySystem
{
    public override void Initialize()
    {
        base.Initialize();
        SubscribeLocalEvent<WaterReservoirComponent, ComponentInit>(OnReservoirInit);
        SubscribeLocalEvent<WaterConsumerComponent, ComponentInit>(OnConsumerInit);

        SubscribeLocalEvent<WaterReservoirComponent, ComponentRemove>(OnReservoirRemoved);
        SubscribeLocalEvent<WaterConsumerComponent, ComponentRemove>(OnConsumerRemoved);

        SubscribeLocalEvent<WaterReservoirComponent, AnchorStateChangedEvent>(OnAnchorChanged);
        SubscribeLocalEvent<WaterConsumerComponent, AnchorStateChangedEvent>(OnAnchorChanged);
    }

    private void OnReservoirInit(EntityUid uid, WaterReservoirComponent comp, ComponentInit args)
    {
        comp.TryAttachToNet(EntMan);
    }

    private void OnConsumerInit(EntityUid uid, WaterConsumerComponent comp, ComponentInit args)
    {
        comp.TryAttachToNet(EntMan);
    }

    private void OnReservoirRemoved(EntityUid uid, WaterReservoirComponent comp, ComponentRemove args)
    {
        comp.DetachFromNet();
    }

    private void OnConsumerRemoved(EntityUid uid, WaterConsumerComponent comp, ComponentRemove args)
    {
        comp.DetachFromNet();
    }

    private void OnAnchorChanged(EntityUid uid, WaterReservoirComponent comp, ref AnchorStateChangedEvent args)
    {
        comp.DetachFromNet();
        comp.TryAttachToNet(EntMan);
    }

    private void OnAnchorChanged(EntityUid uid, WaterConsumerComponent comp, ref AnchorStateChangedEvent args)
    {
        comp.DetachFromNet();
        comp.TryAttachToNet(EntMan);
    }
}


