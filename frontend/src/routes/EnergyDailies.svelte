<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '../lib/api';
  import type { EnergyDaily, EnergySummary, Workshop } from '../lib/types';

  let rows: EnergyDaily[] = [];
  let workshops: Workshop[] = [];
  let summary: EnergySummary | null = null;
  let error = '';
  let editingId: number | null = null;

  function dateStr(d: Date): string {
    const local = new Date(d.getTime() - d.getTimezoneOffset() * 60000);
    return local.toISOString().slice(0, 10);
  }

  const today = new Date();
  const weekAgo = new Date();
  weekAgo.setDate(weekAgo.getDate() - 6);

  let filter = {
    workshopId: '',
    start: dateStr(weekAgo),
    end: dateStr(today),
  };

  let form = {
    workshopId: '',
    workDate: dateStr(today),
    kwh: '',
    peakKw: '',
  };

  function queryString(): string {
    const params = new URLSearchParams();
    if (filter.workshopId) params.set('workshopId', filter.workshopId);
    if (filter.start) params.set('start', filter.start);
    if (filter.end) params.set('end', filter.end);
    const qs = params.toString();
    return qs ? `?${qs}` : '';
  }

  async function load() {
    error = '';
    try {
      const qs = queryString();
      [rows, summary] = await Promise.all([
        api<EnergyDaily[]>(`/energy-dailies${qs}`),
        api<EnergySummary>(`/energy-dailies/summary${qs}`),
      ]);
    } catch (e) {
      error = e instanceof Error ? e.message : '加载失败';
    }
  }

  onMount(async () => {
    try {
      workshops = await api<Workshop[]>('/workshops');
      if (workshops[0]) {
        filter.workshopId = String(workshops[0].id);
        form.workshopId = String(workshops[0].id);
      }
    } catch (e) {
      error = e instanceof Error ? e.message : '加载失败';
      return;
    }
    await load();
  });

  function workshopLabel(id: number): string {
    const w = workshops.find((x) => x.id === id);
    return w ? w.name : `#${id}`;
  }

  function reset() {
    form = {
      workshopId: workshops[0] ? String(workshops[0].id) : '',
      workDate: dateStr(new Date()),
      kwh: '',
      peakKw: '',
    };
    editingId = null;
  }

  function edit(row: EnergyDaily) {
    editingId = row.id;
    form = {
      workshopId: String(row.workshopId),
      workDate: row.workDate,
      kwh: String(row.kwh),
      peakKw: row.peakKw === null ? '' : String(row.peakKw),
    };
  }

  async function save() {
    error = '';
    const numOrNull = (v: unknown) =>
      v === '' || v === undefined || v === null ? null : Number(v);
    const payload = {
      workshopId: Number(form.workshopId),
      workDate: form.workDate,
      kwh: numOrNull(form.kwh),
      peakKw: numOrNull(form.peakKw),
    };
    try {
      if (editingId) {
        await api(`/energy-dailies/${editingId}`, {
          method: 'PUT',
          body: JSON.stringify(payload),
        });
      } else {
        await api('/energy-dailies', { method: 'POST', body: JSON.stringify(payload) });
      }
      reset();
      await load();
    } catch (e) {
      error = e instanceof Error ? e.message : '保存失败';
    }
  }

  async function remove(id: number) {
    if (!confirm('确认删除该能耗日报？')) return;
    try {
      await api(`/energy-dailies/${id}`, { method: 'DELETE' });
      await load();
    } catch (e) {
      error = e instanceof Error ? e.message : '删除失败';
    }
  }
</script>

<header class="page-head">
  <h1>能耗日报</h1>
  <p>按车间登记每日用电量(kWh)与峰值功率(kW)，同车间同日唯一</p>
</header>

{#if error}
  <div class="err">{error}</div>
{/if}

<section class="panel">
  <h2>筛选</h2>
  <div class="fields">
    <div class="field">
      <label>车间
        <select bind:value={filter.workshopId} on:change={load}>
          <option value="">全部车间</option>
          {#each workshops as w}
            <option value={String(w.id)}>{w.name}</option>
          {/each}
        </select>
      </label>
    </div>
    <div class="field"><label>开始日期<input type="date" bind:value={filter.start} on:change={load} /></label></div>
    <div class="field"><label>结束日期<input type="date" bind:value={filter.end} on:change={load} /></label></div>
    <div class="field total-field">
      <span class="total-label">区间合计</span>
      <span class="total-value">{summary ? summary.totalKwh.toFixed(2) : '—'} kWh</span>
      <span class="total-days">{summary ? `${summary.days} 天` : ''}</span>
    </div>
  </div>
</section>

<section class="panel">
  <h2>{editingId ? '编辑日报' : '新增日报'}</h2>
  <div class="fields">
    <div class="field">
      <label>车间
        <select bind:value={form.workshopId}>
          {#each workshops as w}
            <option value={String(w.id)}>{w.name}</option>
          {/each}
        </select>
      </label>
    </div>
    <div class="field"><label>日期<input type="date" bind:value={form.workDate} /></label></div>
    <div class="field"><label>用电量(kWh)<input type="number" min="0" step="0.01" bind:value={form.kwh} /></label></div>
    <div class="field"><label>峰值功率(kW，可空)<input type="number" min="0" step="0.01" bind:value={form.peakKw} /></label></div>
  </div>
  <div class="actions">
    <button class="btn-primary" on:click={save}>{editingId ? '保存' : '创建'}</button>
    {#if editingId}
      <button class="btn-ghost" on:click={reset}>取消</button>
    {/if}
  </div>
</section>

<section class="panel">
  <table class="data-table">
    <thead>
      <tr>
        <th>ID</th>
        <th>车间</th>
        <th>日期</th>
        <th>用电量(kWh)</th>
        <th>峰值功率(kW)</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      {#each rows as row}
        <tr>
          <td>{row.id}</td>
          <td>{workshopLabel(row.workshopId)}</td>
          <td>{row.workDate}</td>
          <td>{row.kwh.toFixed(2)}</td>
          <td>{row.peakKw === null ? '—' : row.peakKw.toFixed(2)}</td>
          <td class="ops">
            <button class="link-btn" on:click={() => edit(row)}>编辑</button>
            <button class="link-btn danger" on:click={() => remove(row.id)}>删除</button>
          </td>
        </tr>
      {:else}
        <tr><td colspan="6">暂无数据</td></tr>
      {/each}
    </tbody>
  </table>
</section>

<style>
  .total-field {
    display: flex;
    align-items: baseline;
    gap: 0.6rem;
    padding: 0.55rem 0.9rem;
    border: 1px solid var(--line);
    background: rgba(192, 57, 43, 0.08);
  }

  .total-label {
    color: var(--steel);
    font-size: 0.85rem;
  }

  .total-value {
    font-family: var(--font-display);
    font-size: 1.35rem;
    color: var(--vermillion-400);
    letter-spacing: 0.03em;
  }

  .total-days {
    color: var(--steel);
    font-size: 0.8rem;
  }
</style>
