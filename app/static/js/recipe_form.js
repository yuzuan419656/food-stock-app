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

            const unitInput =
                row.querySelector(
                    "[data-unit-input]"
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

            hideNewIngredientFields();
        }

        setupYieldFields();

        form.querySelectorAll(
            "[data-ingredient-row]"
        ).forEach(setupIngredientRow);
    }
);