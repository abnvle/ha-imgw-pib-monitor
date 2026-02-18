/**
 * IMGW Weather Card — Modern Design with HA Icons
 */
const CARD_VERSION = "2.0.0";
const DAYS_PL = ["niedz.", "pon.", "wt.", "śr.", "czw.", "pt.", "sob."];

/* ─── Condition → HA icon mapping ──────────────────────────────────── */

const CONDITION_ICONS = {
  sunny: "mdi:weather-sunny",
  "clear-night": "mdi:weather-night",
  partlycloudy: "mdi:weather-partly-cloudy",
  cloudy: "mdi:weather-cloudy",
  rainy: "mdi:weather-rainy",
  pouring: "mdi:weather-pouring",
  snowy: "mdi:weather-snowy",
  "snowy-rainy": "mdi:weather-snowy-rainy",
  fog: "mdi:weather-fog",
  exceptional: "mdi:weather-lightning",
  lightning: "mdi:weather-lightning",
  "lightning-rainy": "mdi:weather-lightning-rainy",
  hail: "mdi:weather-hail",
  windy: "mdi:weather-windy",
  "windy-variant": "mdi:weather-windy-variant",
};

function condIcon(condition) {
  return CONDITION_ICONS[condition] || "mdi:weather-cloudy";
}

/* ─── Helpers ──────────────────────────────────────────────────────── */

function iconFromImgw(ic) {
  if (!ic || ic.length < 6) return "cloudy";
  const c = parseInt(ic[1]) || 0;
  const p = parseInt(ic.substring(3, 5)) || 0;
  const t = ic[ic.length - 1];
  if (p >= 80) return "pouring";
  if (p >= 70) return "snowy";
  if (p >= 60) return "rainy";
  if (p > 0) return "rainy";
  if (c <= 1) return t === "n" ? "clear-night" : "sunny";
  if (c <= 5) return "partlycloudy";
  return "cloudy";
}

function conditionPL(c) {
  return (
    {
      sunny: "S\u0142onecznie",
      "clear-night": "Bezchmurnie",
      partlycloudy: "Cz\u0119\u015bciowe zachmurzenie",
      cloudy: "Pochmurno",
      rainy: "Deszcz",
      pouring: "Ulewny deszcz",
      snowy: "\u015anieg",
      "snowy-rainy": "Deszcz ze \u015bniegiem",
      fog: "Mg\u0142a",
      exceptional: "Burza",
    }[c] || c
  );
}

function fmtTime(d) {
  if (!d) return "--:--";
  const dt = new Date(d);
  return `${dt.getHours().toString().padStart(2, "0")}:${dt.getMinutes().toString().padStart(2, "0")}`;
}

function dayName(dateStr) {
  const d = new Date(dateStr + "T12:00:00");
  const now = new Date();
  const tom = new Date();
  tom.setDate(now.getDate() + 1);
  if (d.toDateString() === now.toDateString()) return "Dzi\u015b";
  if (d.toDateString() === tom.toDateString()) return "Jutro";
  return DAYS_PL[d.getDay()];
}

function round1(v) {
  return v != null ? Math.round(v * 10) / 10 : null;
}

/* ─── Card ─────────────────────────────────────────────────────────── */

class ImgwWeatherCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._activeDay = null;
  }

  setConfig(config) {
    this._config = { show_hourly: true, ...config };
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _findEntity() {
    if (this._config.entity) return this._config.entity;
    const states = this._hass.states;
    const key = Object.keys(states).find(
      (k) => k.startsWith("weather.") && states[k].attributes.icon_imgw !== undefined
    );
    return key || Object.keys(states).find((k) => k.startsWith("weather.imgw")) || null;
  }

  _haIcon(icon, size) {
    return `<ha-icon icon="${icon}" style="--mdc-icon-size:${size}px;width:${size}px;height:${size}px"></ha-icon>`;
  }

  _render() {
    if (!this._hass) return;
    const entityId = this._findEntity();
    if (!entityId || !this._hass.states[entityId]) {
      this.shadowRoot.innerHTML = `<ha-card><div style="padding:24px;color:var(--secondary-text-color)">IMGW Weather entity not found</div></ha-card>`;
      return;
    }

    const e = this._hass.states[entityId];
    const a = e.attributes;
    const name = this._config.name || (a.location ? `IMGW Prognoza \u2014 ${a.location}` : a.friendly_name || "IMGW Prognoza");
    const cond = e.state;
    const temp = a.temperature;
    const feels = a.apparent_temperature;
    const daily = a.daily || [];
    const hourly = (a.hourly || []).slice(0, 12);

    // Group daily by date
    const days = [];
    const dm = {};
    for (const d of daily) {
      const dk = d.date ? d.date.split("T")[0] : "";
      if (!dk) continue;
      if (!dm[dk]) dm[dk] = {};
      if (d.is_day) dm[dk].day = d;
      else dm[dk].night = d;
    }
    for (const [dk, p] of Object.entries(dm)) {
      days.push({
        date: dk,
        hi: p.day?.temp_max ?? p.night?.temp_max ?? null,
        lo: p.night?.temp_min ?? p.day?.temp_min ?? null,
        cond: iconFromImgw(p.day?.icon || p.night?.icon || ""),
        day: p.day,
        night: p.night,
      });
    }

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }

        ha-card {
          padding: 20px;
          color: var(--primary-text-color);
          background: var(--ha-card-background, var(--card-background-color));
          border-radius: var(--ha-card-border-radius, 12px);
          font-family: var(--paper-font-body1_-_font-family, inherit);
          overflow: hidden;
        }

        @keyframes fadeSlide { from{opacity:0;transform:translateY(-6px)} to{opacity:1;transform:translateY(0)} }

        /* ── Header ── */
        .header {
          display: flex; justify-content: space-between; align-items: center;
          margin-bottom: 16px;
        }
        .title {
          font-size: 14px; font-weight: 600; letter-spacing: 0.02em;
          color: var(--primary-text-color); opacity: 0.85;
        }
        .sun-times {
          display: flex; align-items: center; gap: 10px;
          font-size: 11px; color: var(--secondary-text-color); opacity: 0.7;
        }
        .sun-times span {
          display: inline-flex; align-items: center; gap: 2px;
        }
        .sun-times ha-icon {
          --mdc-icon-size: 14px; width: 14px; height: 14px;
          color: var(--secondary-text-color);
        }

        /* ── Current ── */
        .current {
          display: flex; align-items: center; gap: 16px;
          margin-bottom: 20px;
        }
        .icon-main {
          flex-shrink: 0;
          color: var(--state-icon-color, var(--secondary-text-color));
        }
        .icon-main ha-icon {
          --mdc-icon-size: 64px; width: 64px; height: 64px;
        }
        .current-info { flex: 1; min-width: 0; }
        .temp-row { display: flex; align-items: baseline; gap: 4px; }
        .temp {
          font-size: 48px; font-weight: 300; line-height: 1;
          letter-spacing: -1px;
        }
        .temp-unit { font-size: 22px; color: var(--secondary-text-color); font-weight: 300; }
        .condition {
          font-size: 13px; color: var(--secondary-text-color);
          margin-top: 4px;
        }

        /* ── Details bar ── */
        .details {
          display: flex; gap: 6px; flex-wrap: wrap;
          margin-bottom: 20px; padding: 12px 14px;
          background: var(--secondary-background-color, rgba(127,127,127,0.06));
          border-radius: 10px;
        }
        .detail-item {
          display: inline-flex; align-items: center; gap: 4px;
          font-size: 12px; color: var(--secondary-text-color);
          padding: 2px 0; flex: 1 1 auto; white-space: nowrap;
        }
        .detail-item ha-icon {
          --mdc-icon-size: 16px; width: 16px; height: 16px;
          color: var(--secondary-text-color); opacity: 0.7;
        }

        /* ── Separator ── */
        .sep {
          border: none; border-top: 1px solid var(--divider-color, rgba(127,127,127,0.12));
          margin: 0 0 16px;
        }

        /* ── Daily forecast ── */
        .daily { display: flex; gap: 2px; margin-bottom: 4px; }
        .day {
          flex: 1; text-align: center; padding: 10px 2px; border-radius: 10px;
          cursor: pointer; transition: background 0.2s, transform 0.15s;
          min-width: 0;
        }
        .day:hover { background: var(--secondary-background-color, rgba(127,127,127,0.08)); }
        .day:active { transform: scale(0.97); }
        .day.active {
          background: var(--secondary-background-color, rgba(127,127,127,0.12));
        }
        .day-label {
          font-size: 11px; font-weight: 500; color: var(--secondary-text-color);
          margin-bottom: 6px; text-transform: capitalize;
        }
        .day-icon {
          display: flex; justify-content: center; margin-bottom: 6px;
          color: var(--state-icon-color, var(--secondary-text-color));
        }
        .day-icon ha-icon {
          --mdc-icon-size: 28px; width: 28px; height: 28px;
        }
        .day-hi { font-size: 14px; font-weight: 600; }
        .day-lo { font-size: 12px; color: var(--secondary-text-color); opacity: 0.7; margin-top: 2px; }

        /* ── Day detail panel ── */
        .day-detail {
          display: grid; grid-template-columns: 1fr 1fr; gap: 0;
          font-size: 12px; margin-bottom: 16px;
          background: var(--secondary-background-color, rgba(127,127,127,0.06));
          border-radius: 10px; overflow: hidden;
          animation: fadeSlide 0.2s ease;
        }
        .day-detail-col { padding: 12px 14px; }
        .day-detail-col:first-child {
          border-right: 1px solid var(--divider-color, rgba(127,127,127,0.1));
        }
        .day-detail-title {
          font-weight: 600; font-size: 11px; text-transform: uppercase;
          letter-spacing: 0.05em; color: var(--secondary-text-color);
          margin-bottom: 8px;
        }
        .day-detail-row {
          display: flex; justify-content: space-between; align-items: center;
          padding: 3px 0;
        }
        .day-detail-row .lbl { color: var(--secondary-text-color); }
        .day-detail-row .val { font-weight: 500; }

        /* ── Hourly forecast ── */
        .hourly-section { margin-top: 16px; }
        .hourly {
          display: flex; gap: 2px; overflow-x: auto; padding-bottom: 6px;
          scrollbar-width: thin;
          scrollbar-color: var(--secondary-background-color, rgba(127,127,127,0.15)) transparent;
        }
        .hourly::-webkit-scrollbar { height: 4px; }
        .hourly::-webkit-scrollbar-thumb {
          background: var(--secondary-background-color, rgba(127,127,127,0.2));
          border-radius: 2px;
        }
        .hour {
          flex: 0 0 56px; text-align: center; padding: 8px 2px;
          border-radius: 10px; transition: background 0.15s;
        }
        .hour:hover { background: var(--secondary-background-color, rgba(127,127,127,0.08)); }
        .hour-t { font-size: 11px; color: var(--secondary-text-color); font-weight: 500; }
        .hour-icon {
          display: flex; justify-content: center; margin: 4px 0;
          color: var(--state-icon-color, var(--secondary-text-color));
        }
        .hour-icon ha-icon {
          --mdc-icon-size: 24px; width: 24px; height: 24px;
        }
        .hour-temp { font-size: 13px; font-weight: 600; }
        .hour-precip {
          font-size: 10px; color: var(--info-color, #42A5F5); min-height: 14px;
          margin-top: 2px; font-weight: 500;
        }
      </style>

      <ha-card>
        <div class="header">
          <span class="title">${name}</span>
          ${a.sunrise ? `
            <div class="sun-times">
              <span><ha-icon icon="mdi:weather-sunset-up"></ha-icon> ${fmtTime(a.sunrise)}</span>
              <span><ha-icon icon="mdi:weather-sunset-down"></ha-icon> ${fmtTime(a.sunset)}</span>
            </div>
          ` : ""}
        </div>

        <div class="current">
          <div class="icon-main">${this._haIcon(condIcon(cond), 64)}</div>
          <div class="current-info">
            <div class="temp-row">
              <span class="temp">${round1(temp) ?? "--"}</span>
              <span class="temp-unit">\u00b0C</span>
            </div>
            <div class="condition">${conditionPL(cond)}${feels != null ? ` \u00b7 odczuwalna ${round1(feels)}\u00b0` : ""}</div>
          </div>
        </div>

        <div class="details">
          ${a.humidity != null ? `<div class="detail-item"><ha-icon icon="mdi:water-percent"></ha-icon> ${a.humidity}%</div>` : ""}
          ${a.pressure != null ? `<div class="detail-item"><ha-icon icon="mdi:gauge"></ha-icon> ${a.pressure} hPa</div>` : ""}
          ${a.wind_speed != null ? `<div class="detail-item"><ha-icon icon="mdi:weather-windy"></ha-icon> ${a.wind_speed} m/s</div>` : ""}
          ${a.cloud_coverage != null ? `<div class="detail-item"><ha-icon icon="mdi:cloud-percent-outline"></ha-icon> ${a.cloud_coverage}%</div>` : ""}
        </div>

        ${days.length ? `
          <hr class="sep">
          <div class="daily">
            ${days.map((d, i) => `
              <div class="day ${this._activeDay === i ? "active" : ""}" data-i="${i}">
                <div class="day-label">${dayName(d.date)}</div>
                <div class="day-icon">${this._haIcon(condIcon(d.cond), 28)}</div>
                <div class="day-hi">${d.hi != null ? Math.round(d.hi) + "\u00b0" : ""}</div>
                <div class="day-lo">${d.lo != null ? Math.round(d.lo) + "\u00b0" : ""}</div>
              </div>
            `).join("")}
          </div>
          ${this._activeDay != null && days[this._activeDay] ? this._dayDetail(days[this._activeDay]) : ""}
        ` : ""}

        ${this._config.show_hourly !== false && hourly.length ? `
          <div class="hourly-section">
            <hr class="sep">
            <div class="hourly">
              ${hourly.map((h) => `
                <div class="hour">
                  <div class="hour-t">${fmtTime(h.date)}</div>
                  <div class="hour-icon">${this._haIcon(condIcon(iconFromImgw(h.icon)), 24)}</div>
                  <div class="hour-temp">${h.temp != null ? Math.round(h.temp) + "\u00b0" : ""}</div>
                  <div class="hour-precip">${h.precip > 0 ? h.precip + " mm" : ""}</div>
                </div>
              `).join("")}
            </div>
          </div>
        ` : ""}
      </ha-card>
    `;

    this.shadowRoot.querySelectorAll(".day").forEach((el) => {
      el.addEventListener("click", () => {
        const i = parseInt(el.dataset.i);
        this._activeDay = this._activeDay === i ? null : i;
        this._render();
      });
    });
  }

  _dayDetail(d) {
    const col = (title, data) => {
      if (!data) return "";
      const rows = [
        ["Temp.", `${data.temp_min}\u00b0 \u2013 ${data.temp_max}\u00b0`],
        ["Wiatr", `${data.wind_max ?? "--"} m/s`],
        ["Chmury", `${data.cloud_avg ?? "--"}%`],
        ["Opady", `${data.precip ?? 0} mm`],
      ];
      return `
        <div class="day-detail-col">
          <div class="day-detail-title">${title}</div>
          ${rows.map(([l, v]) => `
            <div class="day-detail-row">
              <span class="lbl">${l}</span>
              <span class="val">${v}</span>
            </div>
          `).join("")}
        </div>
      `;
    };
    return `<div class="day-detail">${col("Dzie\u0144", d.day)}${col("Noc", d.night)}</div>`;
  }

  getCardSize() {
    return 5;
  }

  static getStubConfig() {
    return {};
  }
}

customElements.define("imgw-weather-card", ImgwWeatherCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "imgw-weather-card",
  name: "IMGW Weather",
  description: "Modern IMGW weather card",
  preview: true,
});

console.info(
  `%c IMGW-WEATHER %c v${CARD_VERSION} `,
  "background:#1565C0;color:white;font-weight:bold;border-radius:3px 0 0 3px;padding:2px 6px",
  "background:#333;color:white;border-radius:0 3px 3px 0;padding:2px 6px"
);
