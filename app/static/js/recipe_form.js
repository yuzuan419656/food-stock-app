document.addEventListener(
    "DOMContentLoaded",
    () => {
        const form = document.querySelector(
            ".recipe-form"
        );

        if (!form) {
            return;
        }

        const otherOption = (
            form.dataset.otherOption
            || "その他"
        );

        function setupYieldFields() {
            const yieldTypeInputs =
                form.querySelectorAll(
                    'input[name="yield_type"]'
                );

            const baseServings =
                document.getElementById(
                    "base-servings"
                );

            const fixedYieldText =
                document.getElementById(
                    "fixed-yield-text"
                );

            function updateYieldFields() {
                const selected =
                    form.querySelector(
                        'input[name="yield_type"]:checked'
                    );

                const isFixed = (
                    selected?.value === "fixed"
                );

                baseServings.disabled = isFixed;
                baseServings.required = !isFixed;

                fixedYieldText.disabled = !isFixed;
                fixedYieldText.required = isFixed;
            }

            yieldTypeInputs.forEach(
                (input) => {
                    input.addEventListener(
                        "change",
                        updateYieldFields
                    );
                }
            );

            updateYieldFields();
        }

        function setupCustomOption({
            select,
            customField,
            customInput
        }) {
            function update() {
                const isOther = (
                    !select.disabled
                    && select.value
                        === otherOption
                );

                customField.hidden = !isOther;
                customInput.disabled = !isOther;
                customInput.required = isOther;

                if (!isOther) {
                    customInput.value = "";
                }
            }

            select.addEventListener(
                "change",
                update
            );

            update();

            return {
                update
            };
        }

        function setupIngredientRow(row) {
            const ingredientName =
                row.querySelector(
                    "[data-ingredient-name]"
                );

            const ingredientId =
                row.querySelector(
                    "[data-ingredient-id]"
                );

            const datalist =
                document.getElementById(
                    ingredientName.getAttribute(
                        "list"
                    )
                );

            const unitInput =
                row.querySelector(
                    "[data-unit-input]"
                );

            const newIngredientFields =
                row.querySelector(
                    "[data-new-ingredient-fields]"
                );

            const categorySelect =
                row.querySelector(
                    "[data-category-select]"
                );

            const categoryCustomField =
                row.querySelector(
                    "[data-category-custom-field]"
                );

            const categoryCustomInput =
                row.querySelector(
                    "[data-category-custom-input]"
                );

            const categoryController =
                setupCustomOption({
                    select: categorySelect,
                    customField:
                        categoryCustomField,
                    customInput:
                        categoryCustomInput
                });

            function hideNewIngredientFields() {
                newIngredientFields.hidden = true;

                categorySelect.disabled = true;
                categorySelect.required = false;
                categorySelect.value = "";

                categoryCustomField.hidden = true;

                categoryCustomInput.disabled = true;
                categoryCustomInput.required = false;
                categoryCustomInput.value = "";
            }

            function showNewIngredientFields() {
                newIngredientFields.hidden = false;

                categorySelect.disabled = false;
                categorySelect.required = true;

                categoryController.update();
            }

            function setUnit(unit) {
                unitInput.value = unit || "";
            }

            function updateIngredientSelection() {
                const enteredName =
                    ingredientName.value.trim();

                const matchingOption =
                    Array.from(
                        datalist.options
                    ).find(
                        (option) => (
                            option.value
                            === enteredName
                        )
                    );

                if (matchingOption) {
                    ingredientId.value =
                        matchingOption.dataset.id;

                    hideNewIngredientFields();

                    setUnit(
                        matchingOption.dataset.unit
                    );
                } else {
                    ingredientId.value = "";

                    if (enteredName) {
                        showNewIngredientFields();
                    } else {
                        hideNewIngredientFields();
                    }
                }
            }

            ingredientName.addEventListener(
                "change",
                updateIngredientSelection
            );

            ingredientName.addEventListener(
                "blur",
                updateIngredientSelection
            );

            if (ingredientId.value) {
                hideNewIngredientFields();
            } else if (ingredientName.value.trim()) {
                showNewIngredientFields();
            } else {
                hideNewIngredientFields();
}
        }

        function updateIndexedAttribute(
            element,
            attributeName,
            index
        ) {
            const currentValue =
                element.getAttribute(
                    attributeName
                );

            if (!currentValue) {
                return;
            }

            let updatedValue = currentValue;

            if (attributeName === "name") {
                updatedValue =
                    currentValue.replace(
                        /ingredient_\d+_/g,
                        `ingredient_${index}_`
                    );
            } else {
                updatedValue =
                    currentValue.replace(
                        /-\d+$/g,
                        `-${index}`
                    );
            }

            element.setAttribute(
                attributeName,
                updatedValue
            );
        }

        function renumberIngredientRows(
            container
        ) {
            const rows =
                container.querySelectorAll(
                    "[data-ingredient-row]"
                );

            rows.forEach(
                (row, index) => {
                    const title =
                        row.querySelector(
                            "[data-ingredient-row-title]"
                        );

                    title.textContent =
                        `材料${index + 1}`;

                    row.querySelectorAll(
                        "[name]"
                    ).forEach(
                        (element) => {
                            updateIndexedAttribute(
                                element,
                                "name",
                                index
                            );
                        }
                    );

                    row.querySelectorAll(
                        "[id]"
                    ).forEach(
                        (element) => {
                            updateIndexedAttribute(
                                element,
                                "id",
                                index
                            );
                        }
                    );

                    row.querySelectorAll(
                        "[for]"
                    ).forEach(
                        (element) => {
                            updateIndexedAttribute(
                                element,
                                "for",
                                index
                            );
                        }
                    );

                    row.querySelectorAll(
                        "[list]"
                    ).forEach(
                        (element) => {
                            updateIndexedAttribute(
                                element,
                                "list",
                                index
                            );
                        }
                    );
                }
            );
        }

        function resetIngredientRow(row) {
            row.querySelectorAll(
                'input[type="text"],'
                + 'input[type="hidden"]'
            ).forEach(
                (input) => {
                    input.value = "";
                }
            );

            row.querySelectorAll(
                "select"
            ).forEach(
                (select) => {
                    select.selectedIndex = 0;
                }
            );

            const newIngredientFields =
                row.querySelector(
                    "[data-new-ingredient-fields]"
                );

            const categorySelect =
                row.querySelector(
                    "[data-category-select]"
                );

            const categoryCustomField =
                row.querySelector(
                    "[data-category-custom-field]"
                );

            const categoryCustomInput =
                row.querySelector(
                    "[data-category-custom-input]"
                );

            newIngredientFields.hidden = true;

            categorySelect.disabled = true;
            categorySelect.required = false;

            categoryCustomField.hidden = true;

            categoryCustomInput.disabled = true;
            categoryCustomInput.required = false;
        }

        function updateIngredientDeleteButtons(
            container
        ) {
            const rows =
                container.querySelectorAll(
                    "[data-ingredient-row]"
                );

            rows.forEach(
                (row) => {
                    const deleteButton =
                        row.querySelector(
                            "[data-delete-ingredient-row]"
                        );

                    deleteButton.disabled = (
                        rows.length === 1
                    );
                }
            );
        }

        function setupIngredientRepeater() {
            const container =
                document.getElementById(
                    "recipe-ingredient-rows"
                );

            const addButton =
                document.getElementById(
                    "add-ingredient-row"
                );

            container.querySelectorAll(
                "[data-ingredient-row]"
            ).forEach(setupIngredientRow);

            addButton.addEventListener(
                "click",
                () => {
                    const sourceRow =
                        container.querySelector(
                            "[data-ingredient-row]"
                        );

                    const newRow =
                        sourceRow.cloneNode(true);

                    resetIngredientRow(newRow);
                    container.appendChild(newRow);

                    renumberIngredientRows(
                        container
                    );

                    setupIngredientRow(newRow);

                    updateIngredientDeleteButtons(
                        container
                    );

                    const newIngredientName =
                        newRow.querySelector(
                            "[data-ingredient-name]"
                        );

                    newIngredientName.focus();
                }
            );

            container.addEventListener(
                "click",
                (event) => {
                    const deleteButton =
                        event.target.closest(
                            "[data-delete-ingredient-row]"
                        );

                    if (!deleteButton) {
                        return;
                    }

                    const rows =
                        container.querySelectorAll(
                            "[data-ingredient-row]"
                        );

                    if (rows.length === 1) {
                        return;
                    }

                    const row =
                        deleteButton.closest(
                            "[data-ingredient-row]"
                        );

                    row.remove();

                    renumberIngredientRows(
                        container
                    );

                    updateIngredientDeleteButtons(
                        container
                    );
                }
            );

            renumberIngredientRows(
                container
            );

            updateIngredientDeleteButtons(
                container
            );
        }

        function updateStepIndexedAttribute(
            element,
            attributeName,
            index
        ) {
            const currentValue =
                element.getAttribute(
                    attributeName
                );

            if (!currentValue) {
                return;
            }

            let updatedValue = currentValue;

            if (attributeName === "name") {
                updatedValue =
                    currentValue.replace(
                        /step_\d+_/g,
                        `step_${index}_`
                    );
            } else {
                updatedValue =
                    currentValue.replace(
                        /-\d+$/g,
                        `-${index}`
                    );
            }

            element.setAttribute(
                attributeName,
                updatedValue
            );
        }


        function renumberStepRows(container) {
            const rows =
                container.querySelectorAll(
                    "[data-step-row]"
                );

            rows.forEach(
                (row, index) => {
                    const stepNumber =
                        row.querySelector(
                            "[data-step-number]"
                        );

                    stepNumber.textContent =
                        String(index + 1);

                    row.querySelectorAll(
                        "[name]"
                    ).forEach(
                        (element) => {
                            updateStepIndexedAttribute(
                                element,
                                "name",
                                index
                            );
                        }
                    );

                    row.querySelectorAll(
                        "[id]"
                    ).forEach(
                        (element) => {
                            updateStepIndexedAttribute(
                                element,
                                "id",
                                index
                            );
                        }
                    );

                    row.querySelectorAll(
                        "[for]"
                    ).forEach(
                        (element) => {
                            updateStepIndexedAttribute(
                                element,
                                "for",
                                index
                            );
                        }
                    );
                }
            );
        }


        function resetStepRow(row) {
            const description =
                row.querySelector(
                    "[data-step-description]"
                );

            description.value = "";
        }


        function updateStepDeleteButtons(
            container
        ) {
            const rows =
                container.querySelectorAll(
                    "[data-step-row]"
                );

            rows.forEach(
                (row) => {
                    const deleteButton =
                        row.querySelector(
                            "[data-delete-step-row]"
                        );

                    deleteButton.disabled = (
                        rows.length === 1
                    );
                }
            );
        }


        function setupStepRepeater() {
            const container =
                document.getElementById(
                    "recipe-step-rows"
                );

            const addButton =
                document.getElementById(
                    "add-step-row"
                );

            addButton.addEventListener(
                "click",
                () => {
                    const sourceRow =
                        container.querySelector(
                            "[data-step-row]"
                        );

                    const newRow =
                        sourceRow.cloneNode(true);

                    resetStepRow(newRow);
                    container.appendChild(newRow);

                    renumberStepRows(
                        container
                    );

                    updateStepDeleteButtons(
                        container
                    );

                    const description =
                        newRow.querySelector(
                            "[data-step-description]"
                        );

                    description.focus();
                }
            );

            container.addEventListener(
                "click",
                (event) => {
                    const deleteButton =
                        event.target.closest(
                            "[data-delete-step-row]"
                        );

                    if (!deleteButton) {
                        return;
                    }

                    const rows =
                        container.querySelectorAll(
                            "[data-step-row]"
                        );

                    if (rows.length === 1) {
                        return;
                    }

                    const row =
                        deleteButton.closest(
                            "[data-step-row]"
                        );

                    row.remove();

                    renumberStepRows(
                        container
                    );

                    updateStepDeleteButtons(
                        container
                    );
                }
            );

            renumberStepRows(container);

            updateStepDeleteButtons(
                container
            );
        }

        setupYieldFields();
        setupIngredientRepeater();
        setupStepRepeater();
    }
);