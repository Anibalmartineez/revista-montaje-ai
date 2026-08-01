(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EditorOffsetV2 = root.EditorOffsetV2 || {};
  root.EditorOffsetV2.ObjectTree = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function workGroups(layout, face) {
    const slots = layout.slots.filter((slot) => slot.face === face);
    const grouped = new Map(layout.works.map((work) => [work.id, { work, slots: [] }]));
    const orphan = { work: null, slots: [] };
    for (const slot of slots) {
      const group = grouped.get(slot.work_id);
      if (group) group.slots.push(slot);
      else orphan.slots.push(slot);
    }
    const result = [...grouped.values()].filter((group) => group.slots.length);
    if (orphan.slots.length) result.push(orphan);
    return result;
  }

  function visibleWorkSlotIds(layout, face, workId, hiddenSlotIds) {
    const hidden = hiddenSlotIds instanceof Set ? hiddenSlotIds : new Set(hiddenSlotIds || []);
    return layout.slots
      .filter((slot) => slot.face === face && slot.work_id === workId && !hidden.has(slot.id))
      .map((slot) => slot.id);
  }

  function rangeSelection(layout, face, hiddenSlotIds, anchorId, targetId) {
    const anchor = layout.slots.find((slot) => slot.id === anchorId);
    const target = layout.slots.find((slot) => slot.id === targetId);
    if (!anchor || !target || anchor.face !== face || target.face !== face
        || anchor.work_id !== target.work_id) return [targetId];
    const ids = visibleWorkSlotIds(layout, face, target.work_id, hiddenSlotIds);
    const start = ids.indexOf(anchorId);
    const end = ids.indexOf(targetId);
    if (start < 0 || end < 0) return [targetId];
    return ids.slice(Math.min(start, end), Math.max(start, end) + 1);
  }

  function workVisibilityState(slots, hiddenSlotIds) {
    const hidden = hiddenSlotIds instanceof Set ? hiddenSlotIds : new Set(hiddenSlotIds || []);
    if (!slots.length) return "visible";
    const hiddenCount = slots.filter((slot) => hidden.has(slot.id)).length;
    if (!hiddenCount) return "visible";
    if (hiddenCount === slots.length) return "hidden";
    return "mixed";
  }

  function lockSummary(slot) {
    return ["geometry", "content", "delete"]
      .filter((surface) => Array.isArray(slot.locks?.[surface]) && slot.locks[surface].length)
      .map((surface) => surface === "geometry" ? "G" : surface === "content" ? "C" : "D")
      .join("");
  }

  function node(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }

  class Panel {
    constructor(store, refs, registry, contextProvider, actionIds, advancedSelection, runAction) {
      this.store = store;
      this.refs = refs;
      this.registry = registry;
      this.contextProvider = contextProvider;
      this.actionIds = actionIds;
      this.advancedSelection = advancedSelection;
      this.runAction = runAction;
      this.boundClick = (event) => this.onClick(event);
      this.boundKeyDown = (event) => this.onKeyDown(event);
      refs.marqueeMode.addEventListener("change", () => this.runAction(
        actionIds.MARQUEE_MODE_SET,
        { mode: refs.marqueeMode.value },
      ));
      for (const button of refs.advancedSelectionActionButtons) {
        button.addEventListener("click", () => this.runAction(button.dataset.selectionAction));
      }
      for (const [element, actionId] of [
        [refs.visibilityHideSelection, actionIds.VISIBILITY_HIDE_SELECTION],
        [refs.visibilityIsolateSelection, actionIds.VISIBILITY_ISOLATE_SELECTION],
        [refs.visibilityShowAll, actionIds.VISIBILITY_SHOW_ALL],
        [refs.visibilityRestore, actionIds.VISIBILITY_RESTORE_PREVIOUS],
      ]) element.addEventListener("click", () => this.runAction(actionId));
      refs.objectTree.addEventListener("click", this.boundClick);
      refs.objectTree.addEventListener("keydown", this.boundKeyDown);
      this.unsubscribe = store.subscribe((event) => {
        if (!["cursor", "viewport", "pointer_preview", "marquee_preview", "save_start"]
          .includes(event.type)) this.render();
      });
      this.render();
    }

    item(type, id, level, label, options) {
      const item = node("div", `ev2-tree-item ev2-tree-${type}`);
      item.setAttribute("role", "treeitem");
      item.setAttribute("aria-level", String(level));
      item.setAttribute("tabindex", options?.tabindex || "-1");
      item.dataset.treeNodeType = type;
      item.dataset.treeNodeId = id;
      item.dataset.treeNodeKey = `${type}:${id}`;
      if (options?.expanded !== undefined) item.setAttribute("aria-expanded", String(options.expanded));
      if (options?.selected !== undefined) item.setAttribute("aria-selected", String(options.selected));
      if (options?.disabled) item.setAttribute("aria-disabled", "true");
      item.setAttribute("aria-label", options?.ariaLabel || label);

      if (options?.expandable) {
        const expander = node("button", "ev2-tree-expander", options.expanded ? "▾" : "▸");
        expander.type = "button";
        expander.dataset.treeExpand = type;
        expander.setAttribute("aria-label", `${options.expanded ? "Contraer" : "Expandir"} ${label}`);
        item.append(expander);
      } else item.append(node("span", "ev2-tree-indent", "•"));
      item.append(node("span", "ev2-tree-label", label));
      return item;
    }

    render() {
      const focusedKey = this.refs.objectTree.contains(document.activeElement)
        ? document.activeElement.closest?.("[data-tree-node-key]")?.dataset.treeNodeKey
        : null;
      const hidden = this.store.advancedSelection.hiddenSlotIds;
      const expandedFaces = this.store.advancedSelection.expandedFaceIds;
      const expandedWorks = this.store.advancedSelection.expandedWorkIds;
      const issues = this.advancedSelection.geometryIssueIndex(
        this.store.layout,
        this.store.activeFace,
        hidden,
        this.contextProvider().geometry,
        this.store.arrangement.geometryReference,
      );
      const fragment = document.createDocumentFragment();
      const face = this.store.activeFace;
      const faceSlots = this.store.layout.slots.filter((slot) => slot.face === face);
      const faceOpen = expandedFaces.has(face);
      const faceItem = this.item("face", face, 1, face === "front" ? "Frente" : "Dorso", {
        expanded: faceOpen,
        expandable: true,
        tabindex: "0",
        ariaLabel: `${face === "front" ? "Frente" : "Dorso"}, ${faceSlots.length} slots`,
      });
      faceItem.append(node("span", "ev2-tree-count", String(faceSlots.length)));
      const faceSelect = node("button", "ev2-tree-select", "Seleccionar");
      faceSelect.type = "button";
      faceSelect.dataset.treeSelectFace = face;
      faceSelect.disabled = !faceSlots.some((slot) => !hidden.has(slot.id));
      faceItem.append(faceSelect);
      fragment.append(faceItem);

      if (faceOpen) {
        for (const group of workGroups(this.store.layout, face)) {
          const workId = group.work?.id || "__orphan__";
          const workName = group.work?.name || `Work ausente (${group.slots[0]?.work_id || "—"})`;
          const workOpen = expandedWorks.has(workId);
          const visibility = workVisibilityState(group.slots, hidden);
          const workItem = this.item("work", workId, 2, workName, {
            expanded: workOpen,
            expandable: true,
            disabled: !group.work,
            ariaLabel: `${workName}, ${group.slots.length} slots, visibilidad ${visibility}`,
          });
          workItem.dataset.workId = group.slots[0]?.work_id || "";
          workItem.append(node("span", "ev2-tree-count", String(group.slots.length)));
          if (group.work) {
            const select = node("button", "ev2-tree-select", "Seleccionar");
            select.type = "button";
            select.dataset.treeSelectWork = group.work.id;
            select.disabled = !group.slots.some((slot) => !hidden.has(slot.id));
            const visibilityButton = node(
              "button",
              "ev2-tree-visibility",
              visibility === "hidden" ? "Mostrar" : "Ocultar",
            );
            visibilityButton.type = "button";
            visibilityButton.dataset.treeVisibilityWork = group.work.id;
            visibilityButton.dataset.state = visibility;
            visibilityButton.setAttribute("aria-label", `${visibility === "hidden" ? "Mostrar" : "Ocultar"} work ${workName}; estado ${visibility}`);
            workItem.append(select, visibilityButton);
          }
          fragment.append(workItem);

          if (workOpen) {
            for (const slot of group.slots) {
              const ordinal = this.store.layout.slots.indexOf(slot) + 1;
              const isHidden = hidden.has(slot.id);
              const slotIssues = issues.get(slot.id) || new Set();
              const locks = lockSummary(slot);
              const key = this.store.arrangement.keySlotId === slot.id;
              const label = `#${ordinal} · ${slot.geometry.rotation_deg}°`;
              const details = [
                slot.id,
                `work ${slot.work_id}`,
                `asset ${slot.source.asset_id}`,
                isHidden && "oculto solo en vista",
                locks && `locks ${locks}`,
                slotIssues.size && `problemas ${[...slotIssues].join(", ")}`,
                key && "slot clave",
              ].filter(Boolean).join(" · ");
              const slotItem = this.item("slot", slot.id, 3, label, {
                selected: this.store.selection.has(slot.id),
                disabled: isHidden,
                ariaLabel: details,
              });
              slotItem.title = details;
              slotItem.dataset.workId = slot.work_id;
              if (key) slotItem.append(node("span", "ev2-tree-badge is-key", "K"));
              if (locks) slotItem.append(node("span", "ev2-tree-badge is-lock", locks));
              if (slotIssues.size) slotItem.append(node("span", "ev2-tree-badge is-issue", "!"));
              if (isHidden) slotItem.append(node("span", "ev2-tree-badge is-hidden", "Oculto"));
              const visibilityButton = node("button", "ev2-tree-visibility", isHidden ? "Mostrar" : "Ocultar");
              visibilityButton.type = "button";
              visibilityButton.dataset.treeVisibilitySlot = slot.id;
              visibilityButton.setAttribute("aria-label", `${isHidden ? "Mostrar" : "Ocultar"} slot ${slot.id}`);
              slotItem.append(visibilityButton);
              fragment.append(slotItem);
            }
          }
        }
      }

      for (const otherFace of this.store.layout.faces.enabled.filter((item) => item !== face)) {
        const count = this.store.layout.slots.filter((slot) => slot.face === otherFace).length;
        const other = this.item("face", otherFace, 1, otherFace === "front" ? "Frente" : "Dorso", {
          disabled: true,
          ariaLabel: `${otherFace === "front" ? "Frente" : "Dorso"}, ${count} slots, no editable en esta fase`,
        });
        other.append(node("span", "ev2-tree-count", `${count} · no activo`));
        fragment.append(other);
      }

      this.refs.objectTree.replaceChildren(fragment);
      const visibleCount = faceSlots.filter((slot) => !hidden.has(slot.id)).length;
      this.refs.visibilityCount.textContent = `${visibleCount} visibles · ${faceSlots.length - visibleCount} ocultos en ${face === "front" ? "frente" : "dorso"}.`;
      this.refs.marqueeMode.value = this.store.advancedSelection.marqueeMode;
      const context = this.contextProvider();
      for (const button of this.refs.advancedSelectionActionButtons) {
        button.disabled = !this.registry.isEnabled(button.dataset.selectionAction, context);
      }
      for (const [element, actionId] of [
        [this.refs.visibilityHideSelection, this.actionIds.VISIBILITY_HIDE_SELECTION],
        [this.refs.visibilityIsolateSelection, this.actionIds.VISIBILITY_ISOLATE_SELECTION],
        [this.refs.visibilityShowAll, this.actionIds.VISIBILITY_SHOW_ALL],
        [this.refs.visibilityRestore, this.actionIds.VISIBILITY_RESTORE_PREVIOUS],
      ]) element.disabled = !this.registry.isEnabled(actionId, context);
      this.refs.advancedSelectionFeedback.textContent = this.store.feedback
        || "Selección y visibilidad son temporales; la salida no cambia.";
      const restoreFocus = focusedKey
        ? [...this.refs.objectTree.querySelectorAll("[data-tree-node-key]")]
          .find((item) => item.dataset.treeNodeKey === focusedKey)
        : null;
      if (restoreFocus) restoreFocus.focus({ preventScroll: true });
    }

    onClick(event) {
      const slotToggle = event.target.closest("[data-tree-visibility-slot]");
      if (slotToggle) {
        this.runAction(this.actionIds.VISIBILITY_SLOT_TOGGLE, { slotId: slotToggle.dataset.treeVisibilitySlot });
        return;
      }
      const workToggle = event.target.closest("[data-tree-visibility-work]");
      if (workToggle) {
        this.runAction(this.actionIds.VISIBILITY_WORK_TOGGLE, { workId: workToggle.dataset.treeVisibilityWork });
        return;
      }
      const selectWork = event.target.closest("[data-tree-select-work]");
      if (selectWork) {
        this.runAction(this.actionIds.SELECT_WORK_VISIBLE, { workId: selectWork.dataset.treeSelectWork });
        return;
      }
      const selectFace = event.target.closest("[data-tree-select-face]");
      if (selectFace) {
        this.runAction(this.actionIds.SELECT_FACE_VISIBLE);
        return;
      }
      const expander = event.target.closest("[data-tree-expand]");
      const item = event.target.closest("[role=treeitem]");
      if (expander && item) {
        const kind = expander.dataset.treeExpand;
        const id = item.dataset.treeNodeId;
        const expanded = item.getAttribute("aria-expanded") === "true";
        this.store.setTreeExpanded(kind, id, !expanded);
        return;
      }
      if (item?.dataset.treeNodeType === "slot") this.activateSlot(item, event);
    }

    activateSlot(item, event) {
      const slotId = item.dataset.treeNodeId;
      if (this.store.isSlotHidden(slotId)) {
        this.store.setFeedback("El slot está oculto solo en vista. Muéstralo antes de seleccionarlo.");
        return false;
      }
      let ids = [slotId];
      let mode = "replace";
      if (event.shiftKey && this.store.advancedSelection.treeAnchorSlotId) {
        ids = rangeSelection(
          this.store.layout,
          this.store.activeFace,
          this.store.advancedSelection.hiddenSlotIds,
          this.store.advancedSelection.treeAnchorSlotId,
          slotId,
        );
        mode = "replace";
      } else if (event.ctrlKey || event.metaKey) mode = "toggle";
      this.store.setSelection(ids, mode);
      if (!event.shiftKey) this.store.setTreeAnchor(slotId);
      return true;
    }

    visibleItems() {
      return [...this.refs.objectTree.querySelectorAll("[role=treeitem]")];
    }

    onKeyDown(event) {
      if (event.target.closest?.("button")) return;
      const item = event.target.closest?.("[role=treeitem]");
      if (!item || !this.refs.objectTree.contains(item)) return;
      const items = this.visibleItems();
      const index = items.indexOf(item);
      let target = null;
      if (event.key === "ArrowDown") target = items[Math.min(items.length - 1, index + 1)];
      else if (event.key === "ArrowUp") target = items[Math.max(0, index - 1)];
      else if (event.key === "Home") target = items[0];
      else if (event.key === "End") target = items[items.length - 1];
      else if (event.key === "ArrowRight") {
        if (item.hasAttribute("aria-expanded") && item.getAttribute("aria-expanded") === "false") {
          this.store.setTreeExpanded(item.dataset.treeNodeType, item.dataset.treeNodeId, true);
        } else target = items[index + 1];
      } else if (event.key === "ArrowLeft") {
        if (item.getAttribute("aria-expanded") === "true") {
          this.store.setTreeExpanded(item.dataset.treeNodeType, item.dataset.treeNodeId, false);
        } else {
          const level = Number(item.getAttribute("aria-level"));
          target = [...items.slice(0, index)].reverse().find(
            (candidate) => Number(candidate.getAttribute("aria-level")) < level,
          );
        }
      } else if (event.key === "Enter" || event.key === " ") {
        if (item.dataset.treeNodeType === "slot") this.activateSlot(item, event);
        else if (item.dataset.treeNodeType === "work" && item.dataset.workId) {
          this.runAction(this.actionIds.SELECT_WORK_VISIBLE, { workId: item.dataset.workId });
        } else if (item.dataset.treeNodeType === "face" && item.dataset.treeNodeId === this.store.activeFace) {
          this.runAction(this.actionIds.SELECT_FACE_VISIBLE);
        }
      } else return;
      event.preventDefault();
      event.stopPropagation();
      target?.focus();
    }

    dispose() {
      this.unsubscribe();
      this.refs.objectTree.removeEventListener("click", this.boundClick);
      this.refs.objectTree.removeEventListener("keydown", this.boundKeyDown);
    }
  }

  return Object.freeze({ Panel, lockSummary, rangeSelection, visibleWorkSlotIds, workGroups, workVisibilityState });
});
