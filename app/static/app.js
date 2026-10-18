'use strict';
const $ = selector => document.querySelector(selector);
const input = $('#video-input');
const dropzone = $('#dropzone');
const button = $('#analyze-button');
const preview = $('#video-preview');
const keyInput = $('#api-key');
const errorBox = $('#error');
const progressWrap = $('#progress-wrap');
const progressTitle = $('#progress-title');
const progressDetail = $('#progress-detail');
const results = $('#results');
const retryStatus = $('#retry-status');
let limits = null;
let lastResult = null;
let selectedFile = null;
let previewUrl = null;
let analyzing = false;
let ready = false;
let currentJobId = null;
// Remove keys retained by an older version. New keys stay only in page memory.
try { sessionStorage.removeItem('forte_api_key'); } catch (_) { /* storage may be disabled */ }
$('#service-url').textContent = window.location.origin;

function showError(message) { errorBox.textContent = message; errorBox.hidden = false; }
function hideError() { errorBox.hidden = true; errorBox.textContent = ''; }
function refreshButton() { button.disabled = analyzing || !ready || !limits || !selectedFile || !keyInput.value.trim(); }
keyInput.addEventListener('input', refreshButton);

async function jsonRequest(url, options = {}, timeout = 15000) {
  let response;
  try {
    response = await fetch(url, { ...options, cache: 'no-store', signal: AbortSignal.timeout(Math.max(1, timeout)) });
  } catch (error) {
    throw new Error(error.name === 'TimeoutError' || error.name === 'AbortError'
      ? 'Сервис не ответил вовремя. Проверьте соединение и номер проверки.'
      : 'Нет соединения с сервисом. Проверьте адрес и доступность сервера.');
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const messages = {
      401: 'Неверный или отсутствующий X-API-Key. Получите ключ у команды.',
      404: 'Проверка не найдена или срок хранения истёк. Загрузите видео повторно.',
      413: 'Размер файла или запроса превышает лимит сервиса.',
      415: 'Сервис принимает видео в формате MOV.',
      422: 'Файл не прошёл проверку: проверьте кодек, длительность и разрешение MOV.',
      429: 'Сервис занят другой проверкой. Дождитесь её завершения и повторите загрузку.',
      503: 'Модели ещё не готовы. Повторите попытку после запуска сервиса.'
    };
    throw new Error(messages[response.status] || (typeof body.detail === 'string' ? body.detail : 'Ошибка сервера. Сообщите команде номер проверки.'));
  }
  return body;
}

async function checkService() {
  try {
    limits = await jsonRequest('/api/v1/capabilities');
    $('#upload-limits').textContent = `Формат MOV · до ${limits.max_video_mb} МиБ · до ${limits.max_duration_seconds} секунд`;
    ready = true;
    try {
      await jsonRequest('/ready');
      $('#service-status').textContent = 'Модели готовы к проверке';
      $('#service-status').dataset.ready = 'true';
    } catch (_) {
      $('#service-status').textContent = 'Сервис доступен. Модели загрузятся заново при следующей проверке.';
      $('#service-status').dataset.ready = 'false';
    }
  } catch (_) {
    ready = false;
    $('#service-status').textContent = 'Сервис ещё не готов. Повторная проверка через 10 секунд.';
    $('#service-status').dataset.ready = 'false';
  }
  refreshButton();
}
checkService();
setInterval(() => { if (!analyzing) checkService(); }, 10000);

function chooseFile(file) {
  if (!file) return;
  if (analyzing) return showError('Дождитесь завершения текущего анализа');
  if (!limits) return showError('Дождитесь загрузки ограничений сервиса');
  selectedFile = null; refreshButton();
  results.hidden = true; lastResult = null; currentJobId = null;
  retryStatus.hidden = true; progressWrap.hidden = true; $('#job-record').hidden = true;
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  preview.removeAttribute('src'); preview.load(); preview.hidden = true;
  $('#video-empty').hidden = false; $('#preview-note').hidden = true;
  if (!file.name.toLowerCase().endsWith('.mov')) return showError('Выберите видео в формате .mov');
  if (!file.size) return showError('Выбран пустой файл');
  if (file.size > limits.max_video_mb * 1024 * 1024) return showError(`Размер файла превышает ${limits.max_video_mb} МиБ`);
  selectedFile = file;
  previewUrl = URL.createObjectURL(file); preview.src = previewUrl;
  preview.hidden = false; $('#video-empty').hidden = true;
  $('#drop-title').textContent = file.name;
  $('#drop-subtitle').textContent = `${(file.size / 1024 / 1024).toFixed(1)} МиБ · готово к анализу`;
  refreshButton(); hideError();
}
preview.addEventListener('loadedmetadata', () => {
  if (limits && Number.isFinite(preview.duration) && preview.duration > limits.max_duration_seconds) {
    selectedFile = null; refreshButton(); showError(`Длительность превышает ${limits.max_duration_seconds} секунд`);
  }
});
preview.addEventListener('error', () => { if (selectedFile) $('#preview-note').hidden = false; });
input.addEventListener('change', () => chooseFile(input.files[0]));
dropzone.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); input.click(); } });
['dragenter', 'dragover'].forEach(name => dropzone.addEventListener(name, event => { event.preventDefault(); dropzone.classList.add('dragging'); }));
['dragleave', 'drop'].forEach(name => dropzone.addEventListener(name, event => { event.preventDefault(); dropzone.classList.remove('dragging'); }));
dropzone.addEventListener('drop', event => chooseFile(event.dataTransfer.files[0]));

function formatTime(seconds) {
  const minutes = Math.floor(seconds / 60).toString().padStart(2, '0');
  const rest = (seconds % 60).toFixed(1).padStart(4, '0');
  return `${minutes}:${rest}`;
}

async function analyze(resume = false) {
  if (analyzing || (!resume && !selectedFile)) return;
  if (!keyInput.value.trim()) return showError('Введите X-API-Key');
  analyzing = true; refreshButton(); hideError();
  results.hidden = true; retryStatus.hidden = true; progressWrap.hidden = false;
  input.disabled = true; keyInput.disabled = true;
  const started = Date.now();
  const requestKey = keyInput.value.trim();
  const headers = { 'X-API-Key': requestKey };
  const clock = setInterval(() => { $('#progress-time').textContent = formatTime((Date.now() - started) / 1000); }, 500);
  try {
    if (!resume) {
      currentJobId = null; $('#job-id').textContent = '—';
      progressTitle.textContent = 'Загрузка и проверка файла';
      progressDetail.textContent = 'Сервер проверяет формат, размер, длительность и декодирование видео.';
      const form = new FormData(); form.append('file', selectedFile);
      const accepted = await jsonRequest('/api/v1/analyze', { method: 'POST', headers, body: form }, 60000);
      currentJobId = accepted.job_id;
      if (!/^[a-f0-9]{32}$/.test(currentJobId)) throw new Error('Сервис вернул некорректный номер проверки');
    }
    $('#job-id').textContent = currentJobId; $('#job-record').hidden = false;
    progressTitle.textContent = 'Идёт анализ';
    progressDetail.textContent = 'Все модели работают внутри сервиса. Лимит проверки — 5 минут. Точный процент выполнения недоступен.';
    let job;
    while (Date.now() - started < 300000) {
      job = await jsonRequest(`/api/v1/jobs/${currentJobId}`, { headers }, Math.min(15000, 300000 - (Date.now() - started)));
      if (job.status !== 'processing') break;
      await new Promise(resolve => setTimeout(resolve, 1800));
    }
    if (!job || job.status === 'processing') throw new Error('Проверка превысила лимит 5 минут. Сообщите команде номер проверки.');
    if (job.status === 'failed') {
      currentJobId = null;
      throw new Error('Анализ завершился ошибкой. Сообщите команде номер проверки или загрузите видео повторно. Чистый вердикт не выдан.');
    }
    if (job.status !== 'done' || !['violation', 'no_violation'].includes(job.verdict)) throw new Error('Сервис вернул неполный результат');
    progressTitle.textContent = 'Анализ завершён';
    progressDetail.textContent = 'Результат и кадры-доказательства готовы.';
    progressWrap.hidden = true;
    renderResult(job);
  } catch (error) {
    showError(error.message); progressWrap.hidden = true;
    retryStatus.hidden = !currentJobId;
  } finally {
    clearInterval(clock); analyzing = false; input.disabled = false; keyInput.disabled = false;
    refreshButton();
  }
}
button.addEventListener('click', () => analyze());
retryStatus.addEventListener('click', () => analyze(true));

function renderResult(job) {
  lastResult = job;
  const warnings = job.metadata?.warnings || [];
  $('#coverage-note').textContent = warnings.join(' '); $('#coverage-note').hidden = !warnings.length;
  const positive = job.verdict === 'violation';
  $('#verdict-title').textContent = positive ? 'Обнаружены признаки возможных нарушений' : 'Нарушение не обнаружено';
  $('#verdict-badge').textContent = positive ? `Событий: ${job.violations.length} · требуется проверка` : 'Признаки не найдены';
  $('#verdict-badge').className = `verdict ${positive ? 'positive' : 'negative'}`;
  const list = $('#event-list'); list.replaceChildren();
  if (!positive) {
    const note = document.createElement('p'); note.className = 'result-note';
    note.textContent = 'Поддерживаемые проверки не нашли признаков нарушения. Это не подтверждает соблюдение всех процедур. Учитывайте ограничения покрытия.';
    list.append(note);
  }
  for (const event of job.violations) {
    const card = document.createElement('article'); card.className = 'event';
    const time = document.createElement('button'); time.type = 'button'; time.className = 'timecode'; time.textContent = formatTime(event.timecode_sec);
    time.addEventListener('click', () => {
      preview.currentTime = event.timecode_sec;
      preview.play().catch(() => { $('#preview-note').hidden = false; });
      preview.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
    const detail = document.createElement('div');
    const title = document.createElement('h3'); title.textContent = event.type;
    const description = document.createElement('p'); description.textContent = event.description;
    const frames = document.createElement('div'); frames.className = 'frames';
    for (const frame of event.evidence_frames) {
      const figure = document.createElement('figure');
      const image = document.createElement('img'); image.src = `data:image/jpeg;base64,${frame.image_base64}`;
      image.alt = `Кадр-доказательство на ${formatTime(frame.timestamp_sec)}`;
      const full = document.createElement('a'); full.href = image.src; full.download = `evidence-${frame.timestamp_sec.toFixed(1)}.jpg`;
      full.title = 'Скачать полный JPEG-кадр'; full.append(image);
      const caption = document.createElement('figcaption'); caption.textContent = `${formatTime(frame.timestamp_sec)} · полный JPEG`;
      figure.append(full, caption); frames.append(figure);
    }
    const link = document.createElement('a'); link.className = 'rule-link';
    const source = new URL(event.rule.url, window.location.origin);
    if (source.protocol === 'https:' && source.hostname === 'adilet.zan.kz') {
      link.href = source.href; link.target = '_blank'; link.rel = 'noopener noreferrer';
    }
    link.textContent = `${event.rule.document} · ${event.rule.section}`;
    detail.append(title, description, frames, link); card.append(time, detail); list.append(card);
  }
  results.hidden = false; results.focus({ preventScroll: true });
  results.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
$('#download-result').addEventListener('click', () => {
  if (!lastResult) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify(lastResult, null, 2)], { type: 'application/json' }));
  const link = document.createElement('a'); link.href = url; link.download = `review-${lastResult.job_id}.json`;
  link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
});
window.addEventListener('beforeunload', () => { if (previewUrl) URL.revokeObjectURL(previewUrl); });
