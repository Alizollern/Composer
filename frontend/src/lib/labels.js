// Маскировка внутренней кухни: технические события -> человеческий язык.
const ROLE = {
  orchestrator: "Координация работы",
  researcher: "Сбор информации",
  analyst: "Анализ данных",
  writer: "Подготовка материалов",
  standards_creator: "Разработка стандартов",
  standards_editor: "Редактура и вычитка",
  advisor: "Экспертные рекомендации",
  employee_assistant: "Поддержка команды",
};
const TOOL = {
  web_search: "Поиск в интернете",
  fetch_url: "Изучение источника",
  search_knowledge: "Поиск в базе знаний",
  read_knowledge: "Изучение материалов",
  list_knowledge: "Просмотр базы знаний",
  save_knowledge: "Сохранение знаний",
  write_file: "Подготовка документа",
  read_file: "Чтение документа",
  list_files: "Просмотр документов",
  kv_get: "Обращение к памяти",
  kv_set: "Запись в память",
  http_request: "Внешний запрос",
};
export const roleLabel = (n) => ROLE[n] || "Работа над задачей";
export const toolLabel = (n) => TOOL[n] || "Обработка";
export function toolDetail(input) {
  if (!input) return "";
  const v = input.query || input.url || input.path || input.task || input.key || "";
  return typeof v === "string" ? v.slice(0, 120) : "";
}
export function statusLabel(s) {
  return s === "done" ? "Готово" : s === "error" ? "Ошибка" : s === "running" ? "В работе" : s || "";
}
