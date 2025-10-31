using Content.Server.Water.NodeGroups;

namespace Content.Server.Water.EntitySystems;

/// <summary>
/// Система распределения воды внутри каждой сети воды.
/// Простой алгоритм: суммируем доступную подачу и спрос, распределяем пропорционально.
/// </summary>
public sealed class WaterNetSystem : EntitySystem
{
    public override void Update(float frameTime)
    {
        base.Update(frameTime);

        // Перебираем все WaterNet через глобальный список систем узлов не предоставляется напрямую,
        // поэтому используем EntityQuery по компонентам-участникам в сетях для активации.
        // Здесь проще обойти через всех резеруваров и сгруппировать по сети.

        var nets = new Dictionary<WaterNet, (List<Components.WaterReservoirComponent> res, List<Components.WaterConsumerComponent> con)>();

        foreach (var reservoir in EntityManager.EntityQuery<Components.WaterReservoirComponent>())
        {
            if (reservoir.Net is WaterNet net)
            {
                if (!nets.TryGetValue(net, out var tuple))
                {
                    tuple = (new(), new());
                    nets[net] = tuple;
                }
                tuple.res.Add(reservoir);
            }
        }

        foreach (var consumer in EntityManager.EntityQuery<Components.WaterConsumerComponent>())
        {
            if (consumer.Net is WaterNet net)
            {
                if (!nets.TryGetValue(net, out var tuple))
                {
                    tuple = (new(), new());
                    nets[net] = tuple;
                }
                tuple.con.Add(consumer);
            }
        }

        foreach (var kv in nets)
        {
            Distribute(kv.Key, kv.Value.res, kv.Value.con, frameTime);
        }
    }

    private void Distribute(WaterNet net, List<Components.WaterReservoirComponent> reservoirs, List<Components.WaterConsumerComponent> consumers, float frameTime)
    {
        if (reservoirs.Count == 0 || consumers.Count == 0)
        {
            foreach (var c in consumers)
                c.ReceivedLastSecond = 0f;
            return;
        }

        // Доступная подача за кадр
        var totalSupplyPerSecond = 0f;
        foreach (var r in reservoirs)
        {
            var possiblePerSecond = MathF.Min(r.MaxOutputPerSecond, r.CurrentVolume);
            totalSupplyPerSecond += possiblePerSecond;
        }

        var totalDemandPerSecond = 0f;
        foreach (var c in consumers)
            totalDemandPerSecond += MathF.Max(0f, c.DesiredFlowPerSecond);

        if (totalSupplyPerSecond <= 0f)
        {
            foreach (var c in consumers)
                c.ReceivedLastSecond = 0f;
            return;
        }

        var supplyThisFrame = totalSupplyPerSecond * frameTime;
        var demandThisFrame = totalDemandPerSecond * frameTime;

        var scale = demandThisFrame <= 0f ? 0f : MathF.Min(1f, supplyThisFrame / demandThisFrame);

        // Выдаём потребителям
        foreach (var c in consumers)
        {
            var want = c.DesiredFlowPerSecond * frameTime;
            var got = want * scale;
            c.ReceivedLastSecond = got / MathF.Max(frameTime, 0.0001f);
        }

        // Списываем воду из резервуаров пропорционально их способности отдавать
        var totalOutCapacityPerSecond = 0f;
        foreach (var r in reservoirs)
            totalOutCapacityPerSecond += MathF.Min(r.MaxOutputPerSecond, r.CurrentVolume);

        var totalOutThisFrame = MathF.Min(supplyThisFrame, demandThisFrame);
        if (totalOutCapacityPerSecond <= 0f || totalOutThisFrame <= 0f)
            return;

        foreach (var r in reservoirs)
        {
            var cap = MathF.Min(r.MaxOutputPerSecond, r.CurrentVolume);
            var share = cap / totalOutCapacityPerSecond;
            var take = share * totalOutThisFrame;
            r.CurrentVolume = MathF.Max(0f, r.CurrentVolume - take);
        }
    }
}


