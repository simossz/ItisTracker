const $ = (selector) => document.querySelector(selector);
    const normalize = (value) => String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/['’`]/g, "")
      .toUpperCase();
    function searchResultAnnouncement(count, singular, plural, emptyMessage) {
      if (!count) return emptyMessage;
      const message = count === 1 ? `Trovato 1 ${singular}` : `Trovati ${count} ${plural}`;
      return `${message}${count > 40 ? ". Mostrati i primi 40." : "."}`;
    }
    let classManifest, classCalendars, studentManifest, teacherManifest, personLinks, classLinks;
    let studentLoadPromise, teacherLoadPromise;

    async function ensurePersonLinks() {
      if (personLinks) return personLinks;
      try {
        const response = await fetch("/person-pages/links.json", { cache: "no-store" });
        if (response.ok) personLinks = await response.json();
      } catch (error) {
        personLinks = {};
      }
      return personLinks;
    }

    function applyTheme(theme) {
      document.documentElement.dataset.theme = theme;
      localStorage.setItem("itis-theme", theme);
      document.querySelector('meta[name="theme-color"]').content = theme === "dark" ? "#191918" : "#f5f4ef";
      const toggle = $("#theme-toggle");
      if (!toggle) return;
      toggle.setAttribute("aria-label", theme === "dark" ? "Attiva tema chiaro" : "Attiva tema scuro");
      toggle.innerHTML = theme === "dark"
        ? '<svg class="theme-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="4" stroke="currentColor" stroke-width="1.8"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>'
        : '<svg class="theme-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M20 15.1A8.5 8.5 0 0 1 8.9 4a8.5 8.5 0 1 0 11.1 11.1Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>';
    }
    function setTheme(theme) {
      document.documentElement.classList.add("theme-changing");

      const update = () => applyTheme(theme);
      if (document.startViewTransition && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        document.startViewTransition(update).finished.finally(() => {
          document.documentElement.classList.remove("theme-changing");
        });
      } else {
        update();
        window.setTimeout(() => {
          document.documentElement.classList.remove("theme-changing");
        }, 450);
      }
    }
    if ($("#theme-toggle")) {
      $("#theme-toggle").addEventListener("click", () => {
        setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
      });
    }
    setTheme(localStorage.getItem("itis-theme") === "dark" ? "dark" : "light");


    document.querySelectorAll("[data-view]").forEach(button => {
      button.addEventListener("click", () => {
        document.querySelectorAll("[data-view]").forEach(item => {
          const selected = item === button;
          item.classList.toggle("active", selected);
          item.setAttribute("aria-pressed", String(selected));
        });
        document.querySelectorAll(".view").forEach(view => view.classList.remove("active"));
        document.getElementById(button.dataset.view).classList.add("active");
        if (button.dataset.view === "student-view") loadStudents();
        if (button.dataset.view === "teacher-view") loadTeachers();
      });
    });

    function calendarGrid(calendar) {
      const days = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato"];
      const hours = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00"];
      let html = '<div class="calendar-scroll"><div class="calendar-grid"><div class="calendar-head"></div>';
      days.forEach(day => { html += `<div class="calendar-head">${day.slice(0, 3)}</div>`; });
      hours.forEach(hour => {
        html += `<div class="time-label">${hour}</div>`;
        days.forEach(day => {
          const hourNumber = Number(hour.split(":")[0]);
          const lesson = (calendar || []).find(item => {
            if (item.day !== day) return false;
            const start = Number(item.start.split(":")[0]);
            const end = Number(item.end.split(":")[0]);
            return hourNumber >= start && hourNumber < end;
          });
          html += `<div class="calendar-cell${lesson ? "" : " empty-cell"}">`;
          if (lesson) {
            const subject = lesson.subject || lesson.text || "Lezione";
            const className = lesson.class || "";
            const room = lesson.room || "";
            const detailParts = [subject];
            if (className) detailParts.push(className);
            if (room) detailParts.push(room);
            if (lesson.notes?.length) detailParts.push(lesson.notes.join(", "));
            detailParts.push(`${lesson.start}–${lesson.end}`);
            const detail = detailParts.join(" · ");
            const secondary = className || room;
            const extra = className && room ? `<span>${room}</span>` : "";
            html += `<div class="lesson" tabindex="0" data-detail="${detail.replaceAll('"', "&quot;")}"><strong>${subject}</strong>${secondary ? `<small>${secondary}</small>` : ""}${extra}</div>`;
          } else {
            html += '<span aria-label="Ora vuota">—</span>';
          }
          html += "</div>";
        });
      });
      return html + "</div></div>";
    }

    function showClass(name) {
      if (!$("#schedule-wrap")) return;
      if (!classCalendars) {
        $("#schedule-wrap").innerHTML = '<div class="empty">Caricamento orario…</div>';
        return;
      }
      const calendar = classCalendars.classes?.[name]?.lessons || [];
      $("#schedule-wrap").innerHTML = calendar.length ? calendarGrid(calendar) : '<div class="empty">Orario non disponibile.</div>';
    }

    function studentClass(student) {
      return student?.class || student?.schedule_class || "";
    }

    function classRoster(selectedStudent) {
      const selectedClass = studentClass(selectedStudent);
      if (!selectedClass) return '<div class="empty">Classe non disponibile.</div>';
      const classmates = (studentManifest?.students || [])
        .filter(student => studentClass(student) === selectedClass)
        .sort((left, right) => {
          const leftParts = left.name.trim().split(/\s+/);
          const rightParts = right.name.trim().split(/\s+/);
          const leftSurname = leftParts.pop() || "";
          const rightSurname = rightParts.pop() || "";
          return leftSurname.localeCompare(rightSurname, "it", { sensitivity: "base" })
            || left.name.localeCompare(right.name, "it", { sensitivity: "base" });
        });
      if (!classmates.length) return '<div class="empty">Elenco della classe non disponibile.</div>';
      return `<section class="class-roster" aria-label="Elenco della classe" hidden>
        <div class="class-roster-head"><strong>Elenco della classe</strong><span>${classmates.length} studenti</span></div>
        <ul class="class-roster-list">${classmates.map(student => `<li>${student.name}</li>`).join("")}</ul>
      </section>`;
    }

    function enableResultKeyboard(searchInput, resultList) {
      searchInput.addEventListener("keydown", event => {
        if (event.key !== "ArrowDown") return;
        const firstResult = resultList.querySelector(".result-row");
        if (firstResult) {
          event.preventDefault();
          firstResult.focus();
        }
      });

      resultList.addEventListener("keydown", event => {
        const currentResult = event.target.closest(".result-row");
        if (!currentResult) return;
        const results = [...resultList.querySelectorAll(".result-row")];
        const currentIndex = results.indexOf(currentResult);
        let nextIndex = null;

        if (event.key === "ArrowDown") nextIndex = Math.min(currentIndex + 1, results.length - 1);
        if (event.key === "ArrowUp") nextIndex = currentIndex > 0 ? currentIndex - 1 : -1;
        if (event.key === "Home") nextIndex = 0;
        if (event.key === "End") nextIndex = results.length - 1;
        if (event.key === "Escape") {
          event.preventDefault();
          searchInput.focus();
          return;
        }
        if (nextIndex === null) return;

        event.preventDefault();
        if (nextIndex < 0) searchInput.focus();
        else results[nextIndex]?.focus();
      });
    }

    if ($("#student-search")) enableResultKeyboard($("#student-search"), $("#student-results"));
    if ($("#teacher-search")) enableResultKeyboard($("#teacher-search"), $("#teacher-results"));

    async function ensureClassCalendars() {
      if (classCalendars) return classCalendars;
      const response = await fetch("/data/class-calendars.json", { cache: "no-store" });
      if (!response.ok) throw new Error();
      classCalendars = await response.json();
      return classCalendars;
    }

    async function loadClasses() {
      if (!$("#class-select")) return;
      try {
        const classResponse = await fetch("/data/class-schedules.json", { cache: "no-store" });
        if (!classResponse.ok) throw new Error();
        classManifest = await classResponse.json();
        await ensureClassCalendars();
        try {
          const linksResponse = await fetch("/data/class-links.json", { cache: "no-store" });
          if (linksResponse.ok) classLinks = await linksResponse.json();
        } catch (error) {
          classLinks = {};
        }
        const selectedClass = $("#class-select").value;
        const classes = classManifest.classes.filter(item => item.status === "done" && item.local_file);
        $("#class-select").replaceChildren();
        classes.forEach(item => $("#class-select").add(new Option(item.name, item.name)));
        $("#class-select").disabled = false;
        $("#class-select").value = classes.find(item => item.name === selectedClass)?.name
          || classes.find(item => item.name === "1A")?.name
          || classes[0]?.name;
        showClass($("#class-select").value);
      } catch (error) {
        $("#schedule-wrap").innerHTML = '<div class="empty">Orario non disponibile.</div>';
      }
    }
    if ($("#class-select")) $("#class-select").addEventListener("change", event => {
      const url = classLinks?.[event.target.value];
      if (url) window.location.href = url;
      else showClass(event.target.value);
    });

    async function loadStudents() {
      if (!$("#student-search")) return;
      if (studentManifest) return;
      if (studentLoadPromise) return studentLoadPromise;
      studentLoadPromise = (async () => {
        try {
          const response = await fetch("/private-data/student-index.json", { cache: "no-store" });
          if (!response.ok) throw new Error();
          studentManifest = await response.json();
          $("#student-search").disabled = false;
          $("#student-results").innerHTML = '<div class="empty">Scrivi almeno 2 lettere per cercare.</div>';
        } catch (error) {
          $("#student-results").innerHTML = '<div class="empty">Dati non disponibili.</div>';
          $("#student-search-status").textContent = "Dati studenti non disponibili.";
        } finally {
          studentLoadPromise = null;
        }
      })();
      return studentLoadPromise;
    }
    if ($("#student-search")) $("#student-search").addEventListener("input", async event => {
      const query = normalize(event.target.value);
      if (query.length < 2) {
        $("#student-results").innerHTML = '<div class="empty">Scrivi almeno 2 lettere per cercare.</div>';
        $("#student-search-status").textContent = "Scrivi almeno due lettere per cercare.";
        return;
      }
      await ensurePersonLinks();
      const allMatches = (studentManifest?.students || []).filter(student => normalize(student.name).includes(query));
      const matches = allMatches.slice(0, 40);
      $("#student-search-status").textContent = searchResultAnnouncement(
        allMatches.length,
        "studente",
        "studenti",
        "Nessuno studente trovato.",
      );
      $("#student-results").innerHTML = matches.length ? matches.map((student, index) => {
        const studentIndex = studentManifest.students.indexOf(student);
        const href = personLinks?.students?.[String(studentIndex)] || "#";
        return `<a class="result-row result-enter" href="${href}" style="animation-delay:${Math.min(index * 18, 180)}ms"><strong>${student.name}</strong><small>${student.schedule_class || ""}</small></a>`;
      }).join("") : '<div class="empty">Nessuno studente trovato.</div>';
    });

    async function loadTeachers() {
      if (!$("#teacher-search")) return;
      if (teacherManifest) return;
      if (teacherLoadPromise) return teacherLoadPromise;
      teacherLoadPromise = (async () => {
        try {
          const response = await fetch("/private-data/staff-timetables.json", { cache: "no-store" });
          if (!response.ok) throw new Error();
          teacherManifest = await response.json();
          $("#teacher-search").disabled = false;
          $("#teacher-results").innerHTML = '<div class="empty">Scrivi almeno 2 lettere per cercare.</div>';
        } catch (error) {
          $("#teacher-results").innerHTML = '<div class="empty">Dati non disponibili.</div>';
          $("#teacher-search-status").textContent = "Dati docenti non disponibili.";
        } finally {
          teacherLoadPromise = null;
        }
      })();
      return teacherLoadPromise;
    }
    if ($("#teacher-search")) $("#teacher-search").addEventListener("input", event => {
      const query = normalize(event.target.value);
      if (query.length < 2) {
        $("#teacher-results").innerHTML = '<div class="empty">Scrivi almeno 2 lettere per cercare.</div>';
        $("#teacher-search-status").textContent = "Scrivi almeno due lettere per cercare.";
        return;
      }
      const allMatches = (teacherManifest?.teachers || []).filter(teacher => teacher.status === "done" && normalize(teacher.name).includes(query));
      const matches = allMatches.slice(0, 40);
      $("#teacher-search-status").textContent = searchResultAnnouncement(
        allMatches.length,
        "docente",
        "docenti",
        "Nessun docente trovato.",
      );
      $("#teacher-results").innerHTML = matches.length ? matches.map((teacher, index) =>
        `<button class="result-row result-enter" type="button" data-teacher="${teacher.resource_code}" aria-pressed="false" style="animation-delay:${Math.min(index * 18, 180)}ms"><strong>${teacher.name}</strong><small>Orario</small></button>`
      ).join("") : '<div class="empty">Nessun docente trovato.</div>';
      $("#teacher-results").querySelectorAll("[data-teacher]").forEach(button => {
        button.addEventListener("click", () => {
          const teacher = teacherManifest.teachers.find(item => item.resource_code === button.dataset.teacher);
          $("#teacher-results").querySelectorAll("[data-teacher]").forEach(item => {
            const selected = item === button;
            item.classList.toggle("active", selected);
            item.setAttribute("aria-pressed", String(selected));
          });
          $("#teacher-search-status").textContent = `Orario di ${teacher.name} visualizzato.`;
          const personLink = personLinks?.teachers?.[teacher.resource_code];
          const linkHtml = personLink ? `<a class="person-link" href="${personLink}">Apri pagina →</a>` : "";
          const calendar = teacher.lessons || [];
          const fallback = teacher.local_file
            ? `<img src="./${teacher.local_file}" alt="Orario ufficiale di ${teacher.name}">`
            : '<div class="empty">Tabella non ancora disponibile.</div>';
          $("#teacher-detail").innerHTML = `<div class="detail-head"><strong>${teacher.name}</strong>${linkHtml}<span>Anno completo</span></div><div class="detail-body">${calendar.length ? calendarGrid(calendar) : fallback}</div>`;
        });
      });
    });

    const DAY_NAMES = ["Domenica", "Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato"];
    const timeToMinutes = (value) => {
      const [hours, minutes] = String(value || "0:0").split(":").map(Number);
      return hours * 60 + minutes;
    };

    async function loadFreeRooms() {
      const wrap = $("#free-rooms");
      if (!wrap) return;
      try {
        await ensureClassCalendars();
        const now = new Date();
        const day = DAY_NAMES[now.getDay()];
        const minutes = now.getHours() * 60 + now.getMinutes();
        const allRooms = new Set();
        const occupied = new Set();
        Object.values(classCalendars?.classes || {}).forEach(entry => {
          (entry.lessons || []).forEach(lesson => {
            const room = String(lesson.room || "").trim();
            if (!room || /VERIFICARE/i.test(room)) return;
            allRooms.add(room);
            if (lesson.day === day && minutes >= timeToMinutes(lesson.start) && minutes < timeToMinutes(lesson.end)) {
              occupied.add(room);
            }
          });
        });
        const free = [...allRooms].filter(room => !occupied.has(room)).sort((a, b) => a.localeCompare(b, "it"));
        const clock = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
        const weekend = day === "Sabato" || day === "Domenica";
        const outsideHours = minutes < 8 * 60 || minutes >= 15 * 60;
        wrap.innerHTML = `
          <div class="free-summary">
            <strong>${free.length}</strong> aule libere su ${allRooms.size} · ${day} ${clock}
          </div>
          ${weekend ? '<p class="empty">È weekend: non ci sono lezioni in corso.</p>' : ""}
          ${!weekend && outsideHours ? '<p class="empty">Fuori dall\'orario delle lezioni: tutte le aule sono libere.</p>' : ""}
          <div class="free-grid">${free.map(room => `<span class="room-chip">${room}</span>`).join("")}</div>
          ${occupied.size ? `<details class="occupied"><summary>${occupied.size} aule occupate in questo momento</summary><div class="free-grid">${[...occupied].sort((a, b) => a.localeCompare(b, "it")).map(room => `<span class="room-chip occupied-chip">${room}</span>`).join("")}</div></details>` : ""}
        `;
        $("#free-rooms-status").textContent = `${free.length} aule libere su ${allRooms.size}, ${day} alle ${clock}.`;
      } catch (error) {
        wrap.innerHTML = '<div class="empty">Dati orari non disponibili.</div>';
        $("#free-rooms-status").textContent = "Dati orari non disponibili.";
      }
    }

    async function loadPersonPage() {
      const kind = document.body.dataset.page;
      const key = document.body.dataset.person;
      const wrap = $("#person-detail");
      if (!wrap || !key) return;
      try {
        if (kind === "student") {
          if (!studentManifest) {
            const response = await fetch("/private-data/student-index.json", { cache: "no-store" });
            if (!response.ok) throw new Error();
            studentManifest = await response.json();
          }
          const student = studentManifest?.students?.[Number(key)];
          if (!student) throw new Error();
          await ensureClassCalendars();
          const calendar = classCalendars?.classes?.[student.schedule_class]?.lessons || [];
          $("#person-name").textContent = student.name;
          $("#person-label").textContent = `Classe ${studentClass(student)}`;
          wrap.innerHTML = `<div class="detail-head"><button class="class-roster-toggle" type="button" aria-expanded="false">Vedi elenco classe</button><span>${studentClass(student)}</span></div><div class="detail-body">${classRoster(student)}${calendar.length ? calendarGrid(calendar) : '<div class="empty">Orario non disponibile.</div>'}</div>`;
          const rosterToggle = wrap.querySelector(".class-roster-toggle");
          const roster = wrap.querySelector(".class-roster");
          if (roster) {
            rosterToggle.addEventListener("click", () => {
              const isVisible = !roster.hidden;
              roster.hidden = isVisible;
              rosterToggle.textContent = isVisible ? "Vedi elenco classe" : "Nascondi elenco classe";
              rosterToggle.setAttribute("aria-expanded", String(!isVisible));
            });
          } else {
            rosterToggle.hidden = true;
          }
        }
        // Le pagine dei docenti sono già complete in HTML statico: il JS non le modifica.
      } catch (error) {
        wrap.innerHTML = '<div class="empty">Dati non disponibili.</div>';
      }
    }

    const page = document.body.dataset.page || "orario";
    loadClasses();
    setInterval(loadClasses, 6 * 60 * 60 * 1000);
    if (page === "studenti") {
      ensurePersonLinks();
      loadStudents();
    } else if (page === "docenti") {
      ensurePersonLinks();
      loadTeachers();
    } else if (page === "aule-libere") {
      loadFreeRooms();
      setInterval(loadFreeRooms, 5 * 60 * 1000);
      if ($("#free-rooms-refresh")) $("#free-rooms-refresh").addEventListener("click", loadFreeRooms);
    } else if (page === "student" || page === "teacher") {
      loadPersonPage();
    }
